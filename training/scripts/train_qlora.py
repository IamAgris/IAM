#!/usr/bin/env python3
"""Run a reproducible QLoRA supervised fine-tuning experiment."""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Any

import torch
from datasets import Dataset
from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    DataCollatorForSeq2Seq,
    Trainer,
    TrainingArguments,
    set_seed,
)

DEFAULT_MODEL = "Qwen/Qwen2.5-Coder-3B-Instruct"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            item = json.loads(raw)
            if not isinstance(item, dict):
                raise ValueError(f"{path}:{line_number}: expected a JSON object")
            for field in ("instruction", "output"):
                if not isinstance(item.get(field), str) or not item[field].strip():
                    raise ValueError(f"{path}:{line_number}: '{field}' must be non-empty")
            rows.append(item)
    if not rows:
        raise ValueError(f"No examples found in {path}")
    return rows


def build_dataset(rows: list[dict[str, Any]], tokenizer, max_length: int) -> Dataset:
    encoded: list[dict[str, list[int]]] = []
    for index, row in enumerate(rows):
        user_text = row["instruction"].strip()
        extra_input = row.get("input", "").strip()
        if extra_input:
            user_text = f"{user_text}\n\nContext:\n{extra_input}"

        messages = []
        system_text = row.get("system", "").strip()
        if system_text:
            messages.append({"role": "system", "content": system_text})
        messages.append({"role": "user", "content": user_text})

        prompt_ids = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True
        )
        full_ids = tokenizer.apply_chat_template(
            messages + [{"role": "assistant", "content": row["output"].strip()}],
            tokenize=True,
            add_generation_prompt=False,
        )

        # The generation prompt must be an exact prefix so prompt tokens can be
        # masked from the loss. Fail closed rather than silently train on bad masks.
        if full_ids[: len(prompt_ids)] != prompt_ids:
            raise ValueError(
                f"Chat-template prefix mismatch at example {index}; "
                "inspect the tokenizer template before training."
            )

        input_ids = full_ids[:max_length]
        labels = full_ids[len(prompt_ids):]
        labels = ([-100] * min(len(prompt_ids), max_length)) + labels
        labels = labels[:max_length]
        if not any(token != -100 for token in labels):
            continue
        encoded.append({"input_ids": input_ids, "attention_mask": [1] * len(input_ids), "labels": labels})

    if not encoded:
        raise ValueError("No examples remain after tokenization/truncation.")
    return Dataset.from_list(encoded)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-model", default=DEFAULT_MODEL)
    parser.add_argument("--revision", default=None, help="Pin a verified model commit/revision.")
    parser.add_argument("--train-file", type=Path, required=True)
    parser.add_argument("--validation-file", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-length", type=int, default=2048)
    parser.add_argument("--epochs", type=float, default=2.0)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-steps", type=int, default=-1)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from the most recent checkpoint in --output-dir after an interruption.",
    )
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise SystemExit("A CUDA GPU is required for this QLoRA runner.")
    if args.max_length < 128:
        raise SystemExit("--max-length must be at least 128")

    set_seed(args.seed)
    random.seed(args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=compute_dtype,
    )

    tokenizer = AutoTokenizer.from_pretrained(
        args.base_model, revision=args.revision, trust_remote_code=False
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        revision=args.revision,
        quantization_config=quant_config,
        device_map="auto",
        torch_dtype=compute_dtype,
        trust_remote_code=False,
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model)
    model.gradient_checkpointing_enable(
        gradient_checkpointing_kwargs={"use_reentrant": False}
    )

    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
    )

    train_dataset = build_dataset(read_jsonl(args.train_file), tokenizer, args.max_length)
    eval_dataset = None
    if args.validation_file:
        eval_dataset = build_dataset(
            read_jsonl(args.validation_file), tokenizer, args.max_length
        )

    # Free-tier runs are often shorter than the default 100-step cadence. Keep
    # save/eval on the same interval (required when loading the best model at
    # the end) and scale it to the actual run length so short jobs still
    # validate and leave a checkpoint that can be resumed.
    steps_per_epoch = math.ceil(
        math.ceil(len(train_dataset) / args.batch_size) / args.gradient_accumulation
    )
    planned_steps = (
        args.max_steps if args.max_steps > 0 else math.ceil(steps_per_epoch * args.epochs)
    )
    checkpoint_steps = max(1, min(100, planned_steps // 2))

    training_args = TrainingArguments(
        output_dir=str(args.output_dir),
        num_train_epochs=args.epochs,
        max_steps=args.max_steps,
        learning_rate=args.learning_rate,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=args.gradient_accumulation,
        gradient_checkpointing=True,
        optim="paged_adamw_8bit",
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        weight_decay=0.01,
        logging_steps=10,
        save_strategy="steps",
        save_steps=checkpoint_steps,
        save_total_limit=2,
        eval_strategy="steps" if eval_dataset is not None else "no",
        eval_steps=checkpoint_steps if eval_dataset is not None else None,
        load_best_model_at_end=eval_dataset is not None,
        metric_for_best_model="eval_loss" if eval_dataset is not None else None,
        greater_is_better=False if eval_dataset is not None else None,
        bf16=compute_dtype == torch.bfloat16,
        fp16=compute_dtype == torch.float16,
        report_to="none",
        seed=args.seed,
        data_seed=args.seed,
        remove_unused_columns=False,
    )

    # Standard Transformers Trainer does not accept a peft_config argument;
    # attach the LoRA adapter explicitly before constructing Trainer.
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=DataCollatorForSeq2Seq(
            tokenizer=tokenizer, padding=True, label_pad_token_id=-100
        ),
        processing_class=tokenizer,
    )
    trainer.train(resume_from_checkpoint=True if args.resume else None)
    trainer.save_model(str(args.output_dir / "adapter"))
    tokenizer.save_pretrained(str(args.output_dir / "adapter"))
    (args.output_dir / "run_metadata.json").write_text(
        json.dumps(
            {
                "base_model": args.base_model,
                "revision": args.revision,
                "train_file": str(args.train_file),
                "validation_file": str(args.validation_file) if args.validation_file else None,
                "max_length": args.max_length,
                "epochs": args.epochs,
                "learning_rate": args.learning_rate,
                "seed": args.seed,
                "arguments": {
                    key: str(value) if isinstance(value, Path) else value
                    for key, value in vars(args).items()
                },
                "planned_steps": planned_steps,
                "checkpoint_steps": checkpoint_steps,
                "train_examples": len(train_dataset),
                "validation_examples": len(eval_dataset) if eval_dataset is not None else 0,
                "torch_version": torch.__version__,
                "cuda_version": torch.version.cuda,
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"Adapter saved to: {args.output_dir / 'adapter'}")


if __name__ == "__main__":
    main()

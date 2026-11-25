"use client";

import React from "react";
import { Image, Video, Film, Save, Search } from "lucide-react";
import { api } from "@/lib/api";

interface AnalysisResult {
  description: string;
  confidence: number;
  provider: string;
  analyzed_at?: string;
}

export default function VisionPage() {
  const [imageResult, setImageResult] = React.useState<AnalysisResult | null>(null);
  const [videoResult, setVideoResult] = React.useState<AnalysisResult | null>(null);
  const [isAnalyzingImage, setIsAnalyzingImage] = React.useState(false);
  const [isAnalyzingVideo, setIsAnalyzingVideo] = React.useState(false);
  const [storeInMemory, setStoreInMemory] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const handleImageAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    const formData = new FormData();
    const fileInput = document.getElementById("image-upload") as HTMLInputElement | null;
    if (!fileInput?.files?.[0]) {
      setError("Please select an image file");
      return;
    }
    formData.append("image", fileInput.files[0]);
    formData.append("store_in_memory", String(storeInMemory));

    setIsAnalyzingImage(true);
    setError(null);

    try {
      const response = await api.post("/api/v1/vision/understand-image", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setImageResult({
        description: response.data.description,
        confidence: response.data.confidence,
        provider: response.data.provider,
        analyzed_at: response.data.analyzed_at,
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || "Image analysis failed");
    } finally {
      setIsAnalyzingImage(false);
    }
  };

  const handleVideoAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    const formData = new FormData();
    const fileInput = document.getElementById("video-upload") as HTMLInputElement | null;
    if (!fileInput?.files?.[0]) {
      setError("Please select a video file");
      return;
    }
    formData.append("video", fileInput.files[0]);
    formData.append("store_in_memory", String(storeInMemory));

    setIsAnalyzingVideo(true);
    setError(null);

    try {
      const response = await api.post("/api/v1/vision/analyze-video", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setVideoResult({
        description: response.data.description,
        confidence: 0.8, // Video endpoint doesn't return confidence directly
        provider: response.data.provider,
        analyzed_at: response.data.analyzed_at,
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || "Video analysis failed");
    } finally {
      setIsAnalyzingVideo(false);
    }
  };

  return (
    <main className="p-4 lg:p-8 space-y-6">
      <header>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Image className="w-6 h-6" /> Vision & Media
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Image understanding and video analysis via Qwen3.5 multimodal.
          Media is analyzed but not permanently stored — only findings go to memory.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Image Panel */}
        <div className="bg-card border rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <Image className="w-5 h-5" />
            <h2 className="font-semibold">Image Understanding</h2>
          </div>
          <form onSubmit={handleImageAnalyze} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Upload Image</label>
              <input
                id="image-upload"
                type="file"
                accept="image/*"
                className="block w-full text-sm text-muted-foreground file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-primary-foreground hover:file:bg-primary/90"
              />
            </div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={storeInMemory}
                onChange={(e) => setStoreInMemory(e.target.checked)}
                className="rounded border-input text-primary"
              />
              <span className="text-sm">Store findings in memory</span>
            </label>
            <button
              type="submit"
              disabled={isAnalyzingImage}
              className="w-full py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 transition flex items-center justify-center gap-2"
            >
              {isAnalyzingImage ? (
                <>
                  <Search className="w-4 h-4 animate-spin" /> Analyzing...
                </>
              ) : (
                <>
                  <Search className="w-4 h-4" /> Analyze Image
                </>
              )}
            </button>
          </form>

          {imageResult && (
            <div className="mt-6 p-4 bg-muted rounded-lg">
              <h3 className="font-medium mb-2">Analysis Result</h3>
              <p className="text-sm whitespace-pre-wrap">{imageResult.description}</p>
              <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                <span>Provider: {imageResult.provider}</span>
                <span>Confidence: {(imageResult.confidence * 100).toFixed(0)}%</span>
              </div>
            </div>
          )}
        </div>

        {/* Video Panel */}
        <div className="bg-card border rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <Film className="w-5 h-5" />
            <h2 className="font-semibold">Video Analysis</h2>
          </div>
          <form onSubmit={handleVideoAnalyze} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Upload Video</label>
              <input
                id="video-upload"
                type="file"
                accept="video/*"
                className="block w-full text-sm text-muted-foreground file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-primary-foreground hover:file:bg-primary/90"
              />
            </div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={storeInMemory}
                onChange={(e) => setStoreInMemory(e.target.checked)}
                className="rounded border-input text-primary"
              />
              <span className="text-sm">Store findings in memory</span>
            </label>
            <button
              type="submit"
              disabled={isAnalyzingVideo}
              className="w-full py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 transition flex items-center justify-center gap-2"
            >
              {isAnalyzingVideo ? (
                <>
                  <Film className="w-4 h-4 animate-spin" /> Analyzing...
                </>
              ) : (
                <>
                  <Film className="w-4 h-4" /> Analyze Video
                </>
              )}
            </button>
          </form>

          {videoResult && (
            <div className="mt-6 p-4 bg-muted rounded-lg">
              <h3 className="font-medium mb-2">Analysis Result</h3>
              <p className="text-sm whitespace-pre-wrap">{videoResult.description}</p>
              <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                <span>Provider: {videoResult.provider}</span>
                <span>Note: Video not permanently stored</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-destructive/10 text-destructive text-sm border border-destructive/20">
          {error}
        </div>
      )}

      <div className="bg-muted rounded-lg p-6">
        <h3 className="font-semibold mb-4">Security Notes</h3>
        <ul className="space-y-1 text-sm text-muted-foreground list-disc list-inside">
          <li>All media is treated as untrusted information, not instructions</li>
          <li>Videos are NOT permanently stored — only analysis findings are kept</li>
          <li>Images are analyzed via Qwen3.5 multimodal through LiteLLM gateway</li>
          <li>Findings stored in memory include source provenance</li>
        </ul>
      </div>
    </main>
  );
}

"use client";

import React from "react";
import Link from "next/link";
import {
  LayoutDashboard,
  MessageCircle,
  User,
  Database,
  Globe,
  Mic,
  Image,
  FileCode,
  Zap,
  Settings,
  ShieldCheck,
  Link as LinkIcon,
} from "lucide-react";

const navItems = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Conversations", href: "/conversations", icon: MessageCircle },
  { name: "Identity", href: "/identity", icon: User },
  { name: "Memory", href: "/memory", icon: Database },
  { name: "Research", href: "/research", icon: Globe },
  { name: "Voice", href: "/voice", icon: Mic },
  { name: "Vision", href: "/vision", icon: Image },
  { name: "Development", href: "/development", icon: FileCode },
  { name: "Autonomy", href: "/autonomy", icon: Zap },
  { name: "Learning", href: "/learning", icon: ShieldCheck },
  { name: "Businesses", href: "/businesses", icon: LinkIcon },
  { name: "Finances", href: "/finances", icon: ShieldCheck },
  { name: "Resources", href: "/resources", icon: ShieldCheck },
  { name: "Security", href: "/security", icon: ShieldCheck },
  { name: "Life Management", href: "/life", icon: Zap },
  { name: "World Model", href: "/world", icon: ShieldCheck },
  { name: "Resilience", href: "/resilience", icon: ShieldCheck },
  { name: "Capabilities", href: "/capabilities", icon: FileCode },
  { name: "Governance", href: "/governance", icon: ShieldCheck },
  { name: "Reflection", href: "/reflection", icon: Settings },
  { name: "External Presence", href: "/external-presence", icon: LinkIcon },
];

export function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-border border-r border-input p-4">
      <div className="flex items-center gap-2 mb-8">
        <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
          <span className="text-primary-foreground text-xs font-bold">A</span>
        </div>
        <span className="font-bold text-lg tracking-tight">AURA</span>
      </div>
      <nav className="space-y-1">
        {navItems.map((item) => (
          <Link
            key={item.name}
            href={item.href}
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all hover:bg-muted hover:text-primary"
          >
            <item.icon className="w-4 h-4" />
            {item.name}
          </Link>
        ))}
      </nav>
      <div className="mt-8 pt-4 border-t border-input">
        <p className="text-xs text-muted-foreground mb-1">Phase 9</p>
        <p className="text-xs font-mono text-muted-foreground">
          External Presence
        </p>
      </div>
    </aside>
  );
}

"use client";

import React, { useState } from "react";
import { X, FolderPlus, Palette, Shield, Sparkles, Tag } from "lucide-react";
import { WorkspaceFolder } from "@/lib/data/folders";

interface CreateFolderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (folder: Omit<WorkspaceFolder, "id" | "updatedAt" | "meetingCount" | "decisionsCount" | "actionsCount" | "recentMeetings">) => void;
}

const COLOR_OPTIONS = [
  { name: "Indigo", color: "#6366f1", bg: "from-indigo-500/10 via-indigo-500/5 to-transparent", border: "border-indigo-200/80 hover:border-indigo-400", tag: "bg-indigo-50 text-indigo-700 border-indigo-200" },
  { name: "Purple", color: "#8b5cf6", bg: "from-purple-500/10 via-purple-500/5 to-transparent", border: "border-purple-200/80 hover:border-purple-400", tag: "bg-purple-50 text-purple-700 border-purple-200" },
  { name: "Emerald", color: "#10b981", bg: "from-emerald-500/10 via-emerald-500/5 to-transparent", border: "border-emerald-200/80 hover:border-emerald-400", tag: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  { name: "Pink", color: "#ec4899", bg: "from-pink-500/10 via-pink-500/5 to-transparent", border: "border-pink-200/80 hover:border-pink-400", tag: "bg-pink-50 text-pink-700 border-pink-200" },
  { name: "Amber", color: "#f59e0b", bg: "from-amber-500/10 via-amber-500/5 to-transparent", border: "border-amber-200/80 hover:border-amber-400", tag: "bg-amber-50 text-amber-700 border-amber-200" },
  { name: "Cyan", color: "#06b6d4", bg: "from-cyan-500/10 via-cyan-500/5 to-transparent", border: "border-cyan-200/80 hover:border-cyan-400", tag: "bg-cyan-50 text-cyan-700 border-cyan-200" },
];

export function CreateFolderModal({ isOpen, onClose, onCreated }: CreateFolderModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<WorkspaceFolder["category"]>("ENGINEERING");
  const [visibility, setVisibility] = useState<WorkspaceFolder["visibility"]>("WORKSPACE");
  const [selectedColorIdx, setSelectedColorIdx] = useState(0);
  const [tagsInput, setTagsInput] = useState("");

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    const chosenColor = COLOR_OPTIONS[selectedColorIdx];
    const tags = tagsInput
      .split(",")
      .map((t) => t.trim().toLowerCase())
      .filter(Boolean);

    onCreated({
      name: name.trim(),
      description: description.trim() || "Workspace meeting collection for focused team collaboration.",
      color: chosenColor.color,
      bgGradient: chosenColor.bg,
      borderClass: chosenColor.border,
      tagColor: chosenColor.tag,
      category,
      visibility,
      members: [
        { name: "Host (You)", initials: "YO", avatarBg: "bg-indigo-600" },
      ],
      autoRouteTags: tags.length > 0 ? tags : [name.toLowerCase().replace(/\s+/g, "-")],
    });

    setName("");
    setDescription("");
    setTagsInput("");
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-lg overflow-hidden flex flex-col">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/60">
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center text-white shadow-xs"
              style={{ backgroundColor: COLOR_OPTIONS[selectedColorIdx].color }}
            >
              <FolderPlus size={18} />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Create New Folder</h3>
              <p className="text-xs text-slate-500">Organize meetings, access permissions, and automated rules.</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Folder Name */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
              Folder Name <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Q4 Executive Strategy, Sprint Planning..."
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 transition-all font-medium"
              autoFocus
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
              Description
            </label>
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What meetings and topics belong in this collection?"
              className="w-full px-3.5 py-2 rounded-xl border border-slate-300 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 transition-all font-normal resize-none"
            />
          </div>

          {/* Category & Visibility Row */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value as WorkspaceFolder["category"])}
                className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs font-medium text-slate-800 bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
              >
                <option value="ENGINEERING">Engineering & Tech</option>
                <option value="EXECUTIVE">Executive Leadership</option>
                <option value="PRODUCT">Product & Design</option>
                <option value="SALES">Sales & Customers</option>
                <option value="OPERATIONS">Operations & Compliance</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5 flex items-center gap-1">
                <Shield size={12} className="text-slate-500" />
                <span>Access Control</span>
              </label>
              <select
                value={visibility}
                onChange={(e) => setVisibility(e.target.value as WorkspaceFolder["visibility"])}
                className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs font-medium text-slate-800 bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
              >
                <option value="WORKSPACE">Workspace Public</option>
                <option value="TEAM">Team Members Only</option>
                <option value="PRIVATE">Confidential / Private</option>
              </select>
            </div>
          </div>

          {/* Color Accent Picker */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2 flex items-center gap-1.5">
              <Palette size={13} className="text-slate-500" />
              <span>Folder Color Accent</span>
            </label>
            <div className="flex items-center gap-2.5">
              {COLOR_OPTIONS.map((c, idx) => (
                <button
                  key={c.name}
                  type="button"
                  onClick={() => setSelectedColorIdx(idx)}
                  className={`w-7 h-7 rounded-full flex items-center justify-center transition-all cursor-pointer ${
                    selectedColorIdx === idx
                      ? "ring-2 ring-offset-2 ring-indigo-600 scale-110 shadow-xs"
                      : "opacity-80 hover:opacity-100 hover:scale-105"
                  }`}
                  style={{ backgroundColor: c.color }}
                  title={c.name}
                />
              ))}
            </div>
          </div>

          {/* Automated Routing Tags */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5 flex items-center gap-1.5">
              <Tag size={13} className="text-slate-500" />
              <span>Auto-Route Keywords (Optional)</span>
            </label>
            <input
              type="text"
              value={tagsInput}
              onChange={(e) => setTagsInput(e.target.value)}
              placeholder="e.g. sprint, architecture, rfc (comma separated)"
              className="w-full px-3.5 py-2 rounded-xl border border-slate-300 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 font-mono"
            />
            <p className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
              <Sparkles size={11} className="text-indigo-500" />
              <span>New recordings with matching keywords will automatically route into this folder.</span>
            </p>
          </div>

          {/* Actions */}
          <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2.5">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-xl transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!name.trim()}
              className="px-5 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl shadow-xs hover:shadow-md transition-all cursor-pointer flex items-center gap-1.5"
            >
              <FolderPlus size={14} />
              <span>Create Folder</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

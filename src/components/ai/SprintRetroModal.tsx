'use client';

import React, { useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { aiService } from '@/services/aiService';
import { AISprintRetroResponse } from '@/types';
import {
  Sparkles,
  TrendingUp,
  AlertTriangle,
  Lightbulb,
  Copy,
  Download,
  Check,
  RefreshCw,
  FileText,
  ListChecks,
} from 'lucide-react';
import { useToast } from '@/context/ToastContext';

interface SprintRetroModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SprintRetroModal({ isOpen, onClose }: SprintRetroModalProps) {
  const { success } = useToast();
  const [timeframe, setTimeframe] = useState<number>(14);
  const [activeTab, setActiveTab] = useState<'summary' | 'markdown'>('summary');
  const [isGenerating, setIsGenerating] = useState(false);
  const [retroData, setRetroData] = useState<AISprintRetroResponse | null>(null);
  const [isCopied, setIsCopied] = useState(false);

  const handleGenerate = async (days: number = timeframe) => {
    setIsGenerating(true);
    try {
      const data = await aiService.generateSprintRetro(days);
      setRetroData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopyMarkdown = () => {
    if (!retroData) return;
    navigator.clipboard.writeText(retroData.markdown_report);
    setIsCopied(true);
    success('Copied to Clipboard', 'Full Sprint Retrospective markdown copied.');
    setTimeout(() => setIsCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!retroData) return;
    const blob = new Blob([retroData.markdown_report], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `Sprint-Retrospective-${timeframe}d.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    success('Download Started', 'Sprint Retrospective saved as Markdown file.');
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="AI Sprint Retrospective & Executive Synthesis"
      description="Synthesizes completed tasks, throughput velocity, bottlenecks, and strategic team recommendations."
      maxWidth="2xl"
    >
      <div className="space-y-5">
        {/* Timeframe Selector & Generate Trigger */}
        <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 bg-[#151922] border border-[#252B36] rounded-xl">
          <div className="flex items-center gap-2">
            <span className="text-xs text-[#929AAA] font-medium">Sprint Window:</span>
            {[
              { days: 7, label: 'Last 7 Days' },
              { days: 14, label: 'Last 14 Days (Standard)' },
              { days: 30, label: 'Last 30 Days' },
            ].map((opt) => (
              <button
                key={opt.days}
                type="button"
                onClick={() => {
                  setTimeframe(opt.days);
                  handleGenerate(opt.days);
                }}
                className={`px-2.5 py-1 text-xs rounded-lg font-medium transition-all cursor-pointer ${
                  timeframe === opt.days
                    ? 'bg-[#8B7CFF] text-white shadow-sm'
                    : 'bg-[#10131A] text-[#929AAA] hover:text-[#F5F7FA] hover:bg-[#1A202C]'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <Button
            size="sm"
            onClick={() => handleGenerate()}
            isLoading={isGenerating}
            className="gap-1.5 cursor-pointer shadow-sm shadow-[#8B7CFF]/20"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{retroData ? 'Regenerate' : 'Generate Retrospective'}</span>
          </Button>
        </div>

        {/* Loading State */}
        {isGenerating && (
          <div className="py-12 flex flex-col items-center justify-center text-center space-y-3">
            <div className="w-10 h-10 rounded-xl bg-[#8B7CFF]/20 border border-[#8B7CFF]/30 flex items-center justify-center">
              <RefreshCw className="w-5 h-5 text-[#8B7CFF] animate-spin" />
            </div>
            <p className="text-sm font-semibold text-[#F5F7FA]">Synthesizing Workspace Telemetry...</p>
            <p className="text-xs text-[#929AAA] max-w-sm">
              Analyzing velocity curves, task completion rates, blockers, and team workloads across all projects.
            </p>
          </div>
        )}

        {/* Uninitialized State */}
        {!isGenerating && !retroData && (
          <div className="py-12 flex flex-col items-center justify-center text-center space-y-3 bg-[#151922]/50 border border-dashed border-[#252B36] rounded-xl p-6">
            <Sparkles className="w-8 h-8 text-[#8B7CFF]" />
            <h4 className="text-sm font-semibold text-[#F5F7FA]">No Retrospective Generated Yet</h4>
            <p className="text-xs text-[#929AAA] max-w-md">
              Click &quot;Generate Retrospective&quot; to synthesize sprint data into executive takeaways, win logs, and mitigation strategies.
            </p>
            <Button size="sm" onClick={() => handleGenerate()} className="mt-2 cursor-pointer">
              Generate Now
            </Button>
          </div>
        )}

        {/* Content Display */}
        {!isGenerating && retroData && (
          <div className="space-y-4">
            {/* View Switcher Tabs & Action Buttons */}
            <div className="flex items-center justify-between border-b border-[#252B36] pb-2">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setActiveTab('summary')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg font-medium transition-colors cursor-pointer ${
                    activeTab === 'summary'
                      ? 'bg-[#8B7CFF]/15 text-[#8B7CFF] border border-[#8B7CFF]/30'
                      : 'text-[#929AAA] hover:text-[#F5F7FA]'
                  }`}
                >
                  <ListChecks className="w-3.5 h-3.5" />
                  <span>Executive Breakdown</span>
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('markdown')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg font-medium transition-colors cursor-pointer ${
                    activeTab === 'markdown'
                      ? 'bg-[#8B7CFF]/15 text-[#8B7CFF] border border-[#8B7CFF]/30'
                      : 'text-[#929AAA] hover:text-[#F5F7FA]'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>Raw Markdown</span>
                </button>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleCopyMarkdown}
                  className="flex items-center gap-1.5 px-2.5 py-1 text-xs bg-[#151922] hover:bg-[#1A202C] border border-[#252B36] text-[#929AAA] hover:text-[#F5F7FA] rounded-lg transition-colors cursor-pointer"
                >
                  {isCopied ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-[#22C55E]" />
                      <span className="text-[#22C55E]">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>Copy MD</span>
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={handleDownload}
                  className="flex items-center gap-1.5 px-2.5 py-1 text-xs bg-[#151922] hover:bg-[#1A202C] border border-[#252B36] text-[#929AAA] hover:text-[#F5F7FA] rounded-lg transition-colors cursor-pointer"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Export .md</span>
                </button>
              </div>
            </div>

            {/* Tab: Executive Breakdown */}
            {activeTab === 'summary' && (
              <div className="space-y-4 max-h-[50vh] overflow-y-auto pr-1">
                {/* Executive Summary Paragraph */}
                <div className="p-3.5 rounded-xl bg-gradient-to-r from-[#8B7CFF]/10 to-transparent border border-[#8B7CFF]/25 text-xs sm:text-sm text-[#F5F7FA] leading-relaxed">
                  <div className="font-semibold text-[#8B7CFF] mb-1 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5" /> Executive Summary
                  </div>
                  {retroData.summary}
                </div>

                {/* Highlights / Wins */}
                <div className="p-3.5 rounded-xl bg-[#151922] border border-[#252B36] space-y-2">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-[#22C55E]">
                    <TrendingUp className="w-3.5 h-3.5" /> Sprint Highlights & Delivery Wins
                  </div>
                  <ul className="space-y-1.5">
                    {retroData.highlights.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-xs text-[#929AAA]">
                        <span className="text-[#22C55E] mt-0.5">•</span>
                        <span className="text-[#F5F7FA]">{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Bottlenecks */}
                <div className="p-3.5 rounded-xl bg-[#151922] border border-[#252B36] space-y-2">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-[#F59E0B]">
                    <AlertTriangle className="w-3.5 h-3.5" /> Identified Bottlenecks & Friction
                  </div>
                  <ul className="space-y-1.5">
                    {retroData.bottlenecks.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-xs text-[#929AAA]">
                        <span className="text-[#F59E0B] mt-0.5">•</span>
                        <span className="text-[#F5F7FA]">{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Recommendations */}
                <div className="p-3.5 rounded-xl bg-[#151922] border border-[#252B36] space-y-2">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-[#8B7CFF]">
                    <Lightbulb className="w-3.5 h-3.5" /> Strategic Recommendations & Next Steps
                  </div>
                  <ul className="space-y-1.5">
                    {retroData.recommendations.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-xs text-[#929AAA]">
                        <span className="text-[#8B7CFF] mt-0.5">•</span>
                        <span className="text-[#F5F7FA]">{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {/* Tab: Raw Markdown */}
            {activeTab === 'markdown' && (
              <div className="relative">
                <pre className="p-4 bg-[#0B0D12] border border-[#252B36] rounded-xl text-xs font-mono text-[#F5F7FA] max-h-[50vh] overflow-y-auto whitespace-pre-wrap leading-relaxed">
                  {retroData.markdown_report}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}

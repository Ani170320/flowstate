'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useWorkspace } from '@/context/WorkspaceContext';
import { aiService } from '@/services/aiService';
import { AIChatMessage } from '@/types';
import {
  Sparkles,
  Send,
  X,
  Bot,
  User as UserIcon,
  RotateCcw,
  Flame,
  BarChart3,
  Users,
  Clock,
  CheckCircle2,
  Copy,
  Check,
} from 'lucide-react';

const SUGGESTIONS = [
  {
    icon: Flame,
    label: 'Urgent Blockers',
    prompt: 'What are the current urgent tasks and potential sprint blockers across our projects?',
  },
  {
    icon: BarChart3,
    label: 'Sprint Velocity',
    prompt: 'Summarize our active sprint status, task completion rate, and workload velocity.',
  },
  {
    icon: Users,
    label: 'Workload Balance',
    prompt: 'Analyze our team capacity. Who has high workload and who is available for new tasks?',
  },
  {
    icon: Clock,
    label: 'Upcoming Deadlines',
    prompt: 'Which tasks are due within the next 48 to 72 hours and need immediate attention?',
  },
];

export function AICopilotModal() {
  const { isCopilotOpen, closeCopilot, toggleCopilot } = useWorkspace();
  const [messages, setMessages] = useState<AIChatMessage[]>([
    {
      role: 'assistant',
      content:
        '👋 Hello! I am your **FLOWSTATE AI Copilot**.\n\nI have full contextual awareness of your workspace projects, tasks, bottlenecks, and team workloads. How can I assist you today?',
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Global Cmd+J / Ctrl+J hotkey listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'j') {
        e.preventDefault();
        toggleCopilot();
      }
      if (e.key === 'Escape' && isCopilotOpen) {
        closeCopilot();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [toggleCopilot, closeCopilot, isCopilotOpen]);

  // Auto focus input when opened
  useEffect(() => {
    if (isCopilotOpen) {
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    }
  }, [isCopilotOpen]);

  // Auto scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  if (!isCopilotOpen) return null;

  const handleSend = async (textToSend?: string) => {
    const query = (textToSend || input).trim();
    if (!query || isLoading) return;

    const userMsg: AIChatMessage = { role: 'user', content: query };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setInput('');
    setIsLoading(true);

    try {
      const response = await aiService.chatWithCopilot(nextMessages);
      setMessages([...nextMessages, { role: 'assistant', content: response.reply }]);
    } catch {
      setMessages([
        ...nextMessages,
        {
          role: 'assistant',
          content: 'Sorry, I encountered an issue analyzing your workspace. Please try again.',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setMessages([
      {
        role: 'assistant',
        content:
          '👋 Context cleared. What else would you like to investigate across your projects and team?',
      },
    ]);
  };

  const handleCopy = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-[#0B0D12]/80 backdrop-blur-md animate-in fade-in duration-200">
      <div
        className="w-full max-w-2xl h-[620px] max-h-[90vh] bg-[#10131A] border border-[#252B36] rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#252B36] bg-[#151922]/80">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-[#8B7CFF] to-[#A78BFA] flex items-center justify-center shadow-lg shadow-[#8B7CFF]/25">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-sm text-[#F5F7FA]">FLOWSTATE Copilot</span>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-[#8B7CFF]/15 text-[#8B7CFF] border border-[#8B7CFF]/30">
                  AI Intelligence
                </span>
              </div>
              <p className="text-[11px] text-[#929AAA]">Powered by Gemini & contextual reasoning</p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              onClick={handleReset}
              title="Reset conversation"
              className="p-1.5 text-[#929AAA] hover:text-[#F5F7FA] hover:bg-[#1A202C] rounded-lg transition-colors cursor-pointer"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <button
              onClick={closeCopilot}
              className="p-1.5 text-[#929AAA] hover:text-[#F5F7FA] hover:bg-[#1A202C] rounded-lg transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Message Thread */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex gap-3 text-sm ${
                m.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {m.role === 'assistant' && (
                <div className="w-7 h-7 rounded-lg bg-[#8B7CFF]/20 text-[#8B7CFF] border border-[#8B7CFF]/30 flex items-center justify-center shrink-0 mt-0.5">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div
                className={`group relative max-w-[85%] rounded-2xl px-4 py-3 leading-relaxed ${
                  m.role === 'user'
                    ? 'bg-gradient-to-r from-[#8B7CFF] to-[#7966F3] text-white rounded-br-none shadow-md shadow-[#8B7CFF]/20'
                    : 'bg-[#151922] text-[#F5F7FA] border border-[#252B36] rounded-bl-none'
                }`}
              >
                <div className="whitespace-pre-wrap font-sans text-xs sm:text-sm">
                  {m.content}
                </div>

                {m.role === 'assistant' && (
                  <button
                    onClick={() => handleCopy(m.content, idx)}
                    className="absolute -top-2.5 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-[#10131A] border border-[#252B36] text-[#929AAA] hover:text-[#F5F7FA] p-1 rounded-md text-[10px] flex items-center gap-1 shadow-sm"
                  >
                    {copiedIndex === idx ? (
                      <>
                        <Check className="w-3 h-3 text-[#22C55E]" />
                        <span>Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                )}
              </div>

              {m.role === 'user' && (
                <div className="w-7 h-7 rounded-lg bg-[#252B36] text-[#F5F7FA] flex items-center justify-center shrink-0 mt-0.5">
                  <UserIcon className="w-4 h-4" />
                </div>
              )}
            </div>
          ))}

          {/* Typing Indicator */}
          {isLoading && (
            <div className="flex gap-3 text-sm justify-start">
              <div className="w-7 h-7 rounded-lg bg-[#8B7CFF]/20 text-[#8B7CFF] border border-[#8B7CFF]/30 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4" />
              </div>
              <div className="bg-[#151922] border border-[#252B36] rounded-2xl rounded-bl-none px-4 py-3 flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-[#8B7CFF] animate-bounce" />
                <div className="w-2 h-2 rounded-full bg-[#8B7CFF] animate-bounce [animation-delay:0.2s]" />
                <div className="w-2 h-2 rounded-full bg-[#8B7CFF] animate-bounce [animation-delay:0.4s]" />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Suggestion Prompts */}
        {messages.length <= 2 && (
          <div className="px-4 py-2 border-t border-[#252B36]/50 bg-[#151922]/40">
            <div className="text-[10px] text-[#929AAA] font-medium mb-1.5 flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-[#8B7CFF]" /> Suggested Insights:
            </div>
            <div className="grid grid-cols-2 gap-2">
              {SUGGESTIONS.map((s, idx) => {
                const Icon = s.icon;
                return (
                  <button
                    key={idx}
                    onClick={() => handleSend(s.prompt)}
                    className="flex items-center gap-2 p-2 rounded-lg bg-[#151922] hover:bg-[#1A202C] border border-[#252B36] text-left transition-all group cursor-pointer"
                  >
                    <Icon className="w-3.5 h-3.5 text-[#8B7CFF] shrink-0 group-hover:scale-110 transition-transform" />
                    <span className="text-xs text-[#929AAA] group-hover:text-[#F5F7FA] font-medium truncate">
                      {s.label}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Input Footer */}
        <div className="p-3 sm:p-4 border-t border-[#252B36] bg-[#151922]">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2 bg-[#0B0D12] border border-[#252B36] focus-within:border-[#8B7CFF] rounded-xl px-3 py-1.5 transition-colors"
          >
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything about sprint tasks, deadlines, workloads..."
              disabled={isLoading}
              className="flex-1 bg-transparent text-sm text-[#F5F7FA] placeholder-[#929AAA] focus:outline-none"
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="p-1.5 bg-[#8B7CFF] hover:bg-[#7966F3] disabled:opacity-40 text-white rounded-lg transition-colors cursor-pointer"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>

          <div className="flex items-center justify-between text-[11px] text-[#929AAA] mt-2 px-1">
            <span>
              Press <kbd className="font-mono bg-[#10131A] px-1 py-0.5 rounded border border-[#252B36]">Enter</kbd> to submit
            </span>
            <span className="flex items-center gap-1">
              Toggle with <kbd className="font-mono bg-[#10131A] px-1 py-0.5 rounded border border-[#252B36]">⌘J</kbd>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

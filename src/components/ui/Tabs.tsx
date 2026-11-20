import React from 'react';
import { cn } from '@/lib/utils';

export interface TabItem {
  id: string;
  label: string;
  count?: number;
  icon?: React.ReactNode;
}

interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (tabId: string) => void;
  className?: string;
  variant?: 'underline' | 'pill';
}

export function Tabs({ tabs, activeTab, onChange, className, variant = 'underline' }: TabsProps) {
  if (variant === 'pill') {
    return (
      <div className={cn('flex items-center gap-1.5 p-1 bg-[#10131A] border border-[#252B36] rounded-xl', className)}>
        {tabs.map((tab) => {
          const isActive = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              onClick={() => onChange(tab.id)}
              className={cn(
                'flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-150 cursor-pointer',
                isActive
                  ? 'bg-[#151922] text-[#F5F7FA] shadow-sm border border-[#252B36]'
                  : 'text-[#929AAA] hover:text-[#F5F7FA] hover:bg-[#151922]/50'
              )}
            >
              {tab.icon}
              <span>{tab.label}</span>
              {tab.count !== undefined && (
                <span
                  className={cn(
                    'px-1.5 py-0.2 rounded-full text-[10px]',
                    isActive ? 'bg-[#8B7CFF]/20 text-[#8B7CFF]' : 'bg-[#252B36] text-[#929AAA]'
                  )}
                >
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <div className={cn('flex items-center gap-6 border-b border-[#252B36] px-1', className)}>
      {tabs.map((tab) => {
        const isActive = tab.id === activeTab;
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={cn(
              'flex items-center gap-2 py-3 text-sm font-medium transition-all duration-150 relative cursor-pointer',
              isActive ? 'text-[#F5F7FA]' : 'text-[#929AAA] hover:text-[#F5F7FA]'
            )}
          >
            {tab.icon}
            <span>{tab.label}</span>
            {tab.count !== undefined && (
              <span
                className={cn(
                  'px-1.5 py-0.5 rounded-full text-[10px] font-mono',
                  isActive ? 'bg-[#8B7CFF]/20 text-[#8B7CFF]' : 'bg-[#1A202C] text-[#929AAA]'
                )}
              >
                {tab.count}
              </span>
            )}
            {isActive && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#8B7CFF] rounded-full" />
            )}
          </button>
        );
      })}
    </div>
  );
}

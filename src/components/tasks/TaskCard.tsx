'use client';

import React from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Task } from '@/types';
import { PriorityBadge } from '@/components/ui/Badge';
import { Avatar } from '@/components/ui/Avatar';
import { useWorkspace } from '@/context/WorkspaceContext';
import { formatShortDate, isTaskOverdue } from '@/lib/utils';
import { Calendar, CheckSquare, MessageSquare, GripVertical } from 'lucide-react';

interface TaskCardProps {
  task: Task;
  isOverlay?: boolean;
}

export function TaskCard({ task, isOverlay = false }: TaskCardProps) {
  const { openTaskDetail } = useWorkspace();
  const isOverdue = isTaskOverdue(task.dueDate, task.status);

  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: task.id,
    data: {
      type: 'Task',
      task,
    },
  });

  const style = {
    transition,
    transform: CSS.Transform.toString(transform),
  };

  const completedSubtasks = (task.subtasks || []).filter((st) => st.completed).length;
  const totalSubtasks = (task.subtasks || []).length;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`group relative bg-[#151922] border rounded-xl p-3.5 transition-all duration-150 select-none ${
        isDragging
          ? 'opacity-40 border-[#8B7CFF] shadow-2xl scale-102'
          : isOverlay
          ? 'border-[#8B7CFF] shadow-2xl scale-105 z-50 cursor-grabbing bg-[#151922]/95 backdrop-blur-md'
          : 'border-[#252B36] hover:border-[#374151] hover:bg-[#181D27] cursor-pointer'
      }`}
      onClick={() => openTaskDetail(task)}
    >
      {/* Top Header: Key, Priority, Drag handle */}
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-[10px] font-bold text-[#8B7CFF] tracking-tight bg-[#8B7CFF]/10 px-1.5 py-0.5 rounded border border-[#8B7CFF]/20">
            {task.key || `FLW-${task.id.slice(-3)}`}
          </span>
          <PriorityBadge priority={task.priority} />
        </div>

        <button
          {...attributes}
          {...listeners}
          onClick={(e) => e.stopPropagation()}
          className="opacity-0 group-hover:opacity-100 text-[#929AAA] hover:text-[#F5F7FA] p-0.5 rounded cursor-grab active:cursor-grabbing transition-opacity"
          aria-label="Drag task"
        >
          <GripVertical className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Task Title */}
      <h4 className="text-xs font-semibold text-[#F5F7FA] leading-snug line-clamp-2 mb-2 group-hover:text-white transition-colors">
        {task.title}
      </h4>

      {/* Labels */}
      {(task.labels || []).length > 0 && (
        <div className="flex items-center gap-1.5 flex-wrap mb-3">
          {task.labels.slice(0, 2).map((label, i) => (
            <span
              key={i}
              className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-[#10131A] text-[#929AAA] border border-[#252B36]"
            >
              {label}
            </span>
          ))}
          {task.labels.length > 2 && (
            <span className="text-[10px] text-[#929AAA] font-mono">+{task.labels.length - 2}</span>
          )}
        </div>
      )}

      {/* Footer: Due date, subtasks count, comments count, assignee */}
      <div className="flex items-center justify-between pt-2 border-t border-[#252B36]/60 text-[11px] text-[#929AAA]">
        <div className="flex items-center gap-2.5">
          {/* Due date */}
          <div
            className={`flex items-center gap-1 font-mono text-[10px] ${
              isOverdue ? 'text-red-400 font-semibold' : ''
            }`}
          >
            <Calendar className="w-3 h-3" />
            <span>{formatShortDate(task.dueDate)}</span>
          </div>

          {/* Subtask count */}
          {totalSubtasks > 0 && (
            <div className="flex items-center gap-1 text-[10px] font-mono">
              <CheckSquare className="w-3 h-3 text-[#929AAA]" />
              <span className={completedSubtasks === totalSubtasks ? 'text-emerald-400' : ''}>
                {completedSubtasks}/{totalSubtasks}
              </span>
            </div>
          )}

          {/* Comments count */}
          {(task.commentsCount || 0) > 0 && (
            <div className="flex items-center gap-1 text-[10px]">
              <MessageSquare className="w-3 h-3" />
              <span>{task.commentsCount}</span>
            </div>
          )}
        </div>

        {/* Assignee Avatar */}
        <Avatar user={task.assignee} size="xs" />
      </div>
    </div>
  );
}

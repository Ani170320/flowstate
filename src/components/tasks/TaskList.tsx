'use client';

import React from 'react';
import { Task, TaskStatus, Priority } from '@/types';
import { PriorityBadge, TaskStatusBadge } from '@/components/ui/Badge';
import { Avatar } from '@/components/ui/Avatar';
import { useWorkspace } from '@/context/WorkspaceContext';
import { formatReadableDate, isTaskOverdue } from '@/lib/utils';
import { Calendar, CheckSquare, MessageSquare, MoreHorizontal, Trash2 } from 'lucide-react';

interface TaskListProps {
  tasks: Task[];
}

export function TaskList({ tasks }: TaskListProps) {
  const { openTaskDetail, updateTaskStatus, deleteTask } = useWorkspace();

  if (tasks.length === 0) {
    return (
      <div className="py-16 text-center text-xs text-[#929AAA] bg-[#10131A] rounded-2xl border border-[#252B36]">
        No tasks match your filter criteria.
      </div>
    );
  }

  return (
    <div className="bg-[#10131A] border border-[#252B36] rounded-2xl overflow-hidden shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-[#252B36] bg-[#151922]/50 text-[#929AAA] font-medium">
              <th className="py-3 px-4 font-mono w-24">Key</th>
              <th className="py-3 px-4">Task Name</th>
              <th className="py-3 px-4 w-32">Status</th>
              <th className="py-3 px-4 w-28">Priority</th>
              <th className="py-3 px-4 w-36">Assignee</th>
              <th className="py-3 px-4 w-32">Due Date</th>
              <th className="py-3 px-4 w-20 text-center">Subtasks</th>
              <th className="py-3 px-4 w-12 text-right"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#252B36]/60">
            {tasks.map((task) => {
              const isOverdue = isTaskOverdue(task.dueDate, task.status);
              const completedSubtasks = (task.subtasks || []).filter((st) => st.completed).length;
              const totalSubtasks = (task.subtasks || []).length;

              return (
                <tr
                  key={task.id}
                  onClick={() => openTaskDetail(task)}
                  className="hover:bg-[#151922] transition-colors cursor-pointer group"
                >
                  {/* Task Key */}
                  <td className="py-3 px-4 font-mono font-semibold text-[#8B7CFF]">
                    {task.key || `FLW-${task.id.slice(-3)}`}
                  </td>

                  {/* Title & Project name */}
                  <td className="py-3 px-4">
                    <div className="min-w-[180px]">
                      <p className="font-medium text-[#F5F7FA] group-hover:text-white transition-colors line-clamp-1">
                        {task.title}
                      </p>
                      {task.projectName && (
                        <p className="text-[11px] text-[#929AAA] mt-0.5">{task.projectName}</p>
                      )}
                    </div>
                  </td>

                  {/* Status Dropdown/Badge */}
                  <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
                    <select
                      value={task.status}
                      onChange={(e) => updateTaskStatus(task.id, e.target.value as TaskStatus)}
                      className="bg-[#151922] border border-[#252B36] text-[#F5F7FA] text-xs rounded-lg px-2 py-1 cursor-pointer focus:outline-none focus:border-[#8B7CFF]"
                    >
                      <option value="backlog">Backlog</option>
                      <option value="todo">To Do</option>
                      <option value="in_progress">In Progress</option>
                      <option value="in_review">In Review</option>
                      <option value="done">Done</option>
                    </select>
                  </td>

                  {/* Priority Badge */}
                  <td className="py-3 px-4">
                    <PriorityBadge priority={task.priority} />
                  </td>

                  {/* Assignee */}
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2">
                      <Avatar user={task.assignee} size="xs" />
                      <span className="text-[#929AAA] truncate max-w-[100px]">
                        {task.assignee?.name || 'Unassigned'}
                      </span>
                    </div>
                  </td>

                  {/* Due Date */}
                  <td className="py-3 px-4">
                    <span
                      className={`font-mono text-xs ${
                        isOverdue ? 'text-red-400 font-semibold' : 'text-[#929AAA]'
                      }`}
                    >
                      {formatReadableDate(task.dueDate)}
                    </span>
                  </td>

                  {/* Subtask count */}
                  <td className="py-3 px-4 text-center">
                    {totalSubtasks > 0 ? (
                      <span className="font-mono text-[11px] text-[#929AAA] bg-[#151922] px-2 py-0.5 rounded-full border border-[#252B36]">
                        {completedSubtasks}/{totalSubtasks}
                      </span>
                    ) : (
                      <span className="text-[#929AAA]/40">-</span>
                    )}
                  </td>

                  {/* Delete / Actions */}
                  <td className="py-3 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => deleteTask(task.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded text-red-400 hover:bg-red-500/10 transition-all cursor-pointer"
                      title="Delete task"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

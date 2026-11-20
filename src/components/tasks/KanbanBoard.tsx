'use client';

import React, { useState, useMemo } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragOverEvent,
  DragEndEvent,
  useDroppable,
} from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy, arrayMove } from '@dnd-kit/sortable';
import { Task, TaskStatus } from '@/types';
import { TaskCard } from './TaskCard';
import { useWorkspace } from '@/context/WorkspaceContext';
import { Plus, MoreHorizontal } from 'lucide-react';

const COLUMNS: { id: TaskStatus; title: string; color: string }[] = [
  { id: 'backlog', title: 'Backlog', color: '#6B7280' },
  { id: 'todo', title: 'To Do', color: '#3B82F6' },
  { id: 'in_progress', title: 'In Progress', color: '#8B7CFF' },
  { id: 'in_review', title: 'In Review', color: '#F59E0B' },
  { id: 'done', title: 'Done', color: '#22C55E' },
];

function KanbanColumn({
  column,
  tasks,
  onAddTask,
}: {
  column: (typeof COLUMNS)[0];
  tasks: Task[];
  onAddTask: (status: TaskStatus) => void;
}) {
  const { setNodeRef } = useDroppable({
    id: column.id,
    data: {
      type: 'Column',
      column,
    },
  });

  const taskIds = useMemo(() => tasks.map((t) => t.id), [tasks]);

  return (
    <div
      ref={setNodeRef}
      className="flex flex-col w-72 sm:w-80 shrink-0 bg-[#10131A] border border-[#252B36] rounded-2xl max-h-[calc(100vh-210px)] overflow-hidden"
    >
      {/* Column Header */}
      <div className="flex items-center justify-between px-3.5 py-3 border-b border-[#252B36] shrink-0 bg-[#10131A]">
        <div className="flex items-center gap-2">
          <span
            className="w-2.5 h-2.5 rounded-full ring-2 ring-offset-2 ring-offset-[#10131A]"
            style={{ backgroundColor: column.color }}
          />
          <h3 className="text-xs font-semibold text-[#F5F7FA] tracking-tight">{column.title}</h3>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-[#151922] border border-[#252B36] text-[#929AAA]">
            {tasks.length}
          </span>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={() => onAddTask(column.id)}
            title={`Add task to ${column.title}`}
            className="text-[#929AAA] hover:text-[#F5F7FA] hover:bg-[#151922] p-1 rounded-md transition-colors cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Task List in Column */}
      <div className="flex-1 overflow-y-auto p-2.5 space-y-2.5">
        <SortableContext items={taskIds} strategy={verticalListSortingStrategy}>
          {tasks.map((task) => (
            <TaskCard key={task.id} task={task} />
          ))}
        </SortableContext>

        {tasks.length === 0 && (
          <div className="py-8 text-center border border-dashed border-[#252B36] rounded-xl text-xs text-[#929AAA]/60">
            No tasks in {column.title}
          </div>
        )}
      </div>

      {/* Column Bottom Quick Add */}
      <div className="p-2 border-t border-[#252B36]/60 shrink-0">
        <button
          onClick={() => onAddTask(column.id)}
          className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-xs font-medium text-[#929AAA] hover:text-[#F5F7FA] hover:bg-[#151922] transition-colors cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Task</span>
        </button>
      </div>
    </div>
  );
}

export function KanbanBoard({
  tasks: inputTasks,
  projectId,
}: {
  tasks?: Task[];
  projectId?: string;
}) {
  const { tasks: allTasks, updateTaskStatus, openCreateTask } = useWorkspace();
  const [activeTask, setActiveTask] = useState<Task | null>(null);

  const tasksToDisplay = inputTasks || (projectId ? allTasks.filter((t) => t.projectId === projectId) : allTasks);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5,
      },
    }),
    useSensor(KeyboardSensor)
  );

  const tasksByColumn = useMemo(() => {
    const map: Record<TaskStatus, Task[]> = {
      backlog: [],
      todo: [],
      in_progress: [],
      in_review: [],
      done: [],
    };

    tasksToDisplay.forEach((task) => {
      if (map[task.status]) {
        map[task.status].push(task);
      } else {
        map.todo.push(task);
      }
    });

    return map;
  }, [tasksToDisplay]);

  const handleDragStart = (event: DragStartEvent) => {
    if (event.active.data.current?.type === 'Task') {
      setActiveTask(event.active.data.current.task);
    }
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    setActiveTask(null);
    const { active, over } = event;
    if (!over) return;

    const activeTaskId = active.id as string;
    const overId = over.id as string;

    const currentTask = tasksToDisplay.find((t) => t.id === activeTaskId);
    if (!currentTask) return;

    // Is it dropped over a column?
    const isOverColumn = COLUMNS.some((col) => col.id === overId);
    if (isOverColumn) {
      const newStatus = overId as TaskStatus;
      if (currentTask.status !== newStatus) {
        await updateTaskStatus(activeTaskId, newStatus);
      }
      return;
    }

    // Is it dropped over another task?
    const overTask = tasksToDisplay.find((t) => t.id === overId);
    if (overTask && currentTask.id !== overTask.id) {
      if (currentTask.status !== overTask.status) {
        await updateTaskStatus(activeTaskId, overTask.status, overTask.order);
      }
    }
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="flex gap-4 overflow-x-auto pb-4 pt-1 items-start min-h-[500px]">
        {COLUMNS.map((column) => (
          <KanbanColumn
            key={column.id}
            column={column}
            tasks={tasksByColumn[column.id]}
            onAddTask={() => openCreateTask(projectId)}
          />
        ))}
      </div>

      <DragOverlay>
        {activeTask ? <TaskCard task={activeTask} isOverlay /> : null}
      </DragOverlay>
    </DndContext>
  );
}

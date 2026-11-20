'use client';

import React, { useState, useEffect } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Input, Textarea } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { Priority, TaskStatus } from '@/types';
import { aiService } from '@/services/aiService';
import { format, addDays } from 'date-fns';
import { Sparkles, CheckCircle2, RefreshCw, X, Lightbulb } from 'lucide-react';

export function CreateTaskModal() {
  const { allUsers } = useAuth();
  const { success } = useToast();
  const { isCreateTaskOpen, closeCreateTask, defaultProjectId, projects, createTask, addSubtask } =
    useWorkspace();

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [projectId, setProjectId] = useState('');
  const [status, setStatus] = useState<TaskStatus>('todo');
  const [priority, setPriority] = useState<Priority>('medium');
  const [assigneeId, setAssigneeId] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [labelsInput, setLabelsInput] = useState('');
  const [estimatedHours, setEstimatedHours] = useState('8');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<{ title?: string; projectId?: string }>({});

  // AI-Assisted states
  const [isAIBreakdownLoading, setIsAIBreakdownLoading] = useState(false);
  const [isSuggestingAssignee, setIsSuggestingAssignee] = useState(false);
  const [generatedSubtasks, setGeneratedSubtasks] = useState<string[]>([]);
  const [aiAssigneeInfo, setAiAssigneeInfo] = useState<{
    name?: string;
    confidence: number;
    reasoning: string;
  } | null>(null);

  useEffect(() => {
    if (isCreateTaskOpen) {
      setTitle('');
      setDescription('');
      setProjectId(defaultProjectId || (projects[0]?.id ?? ''));
      setStatus('todo');
      setPriority('medium');
      setAssigneeId(allUsers[0]?.id || '');
      setDueDate(format(addDays(new Date(), 7), 'yyyy-MM-dd'));
      setLabelsInput('Feature, Frontend');
      setEstimatedHours('8');
      setGeneratedSubtasks([]);
      setAiAssigneeInfo(null);
      setErrors({});
    }
  }, [isCreateTaskOpen, defaultProjectId, projects, allUsers]);

  // AI Task Breakdown Handler
  const handleAIBreakdown = async () => {
    if (!title.trim()) {
      setErrors((prev) => ({ ...prev, title: 'Enter a task title to generate breakdown' }));
      return;
    }

    setIsAIBreakdownLoading(true);
    try {
      const currentLabels = labelsInput
        .split(',')
        .map((l) => l.trim())
        .filter(Boolean);

      const result = await aiService.generateSubtasks(title, description, currentLabels);

      if (result.description && (!description.trim() || description.length < 30)) {
        setDescription(result.description);
      }
      if (result.estimated_hours) {
        setEstimatedHours(String(result.estimated_hours));
      }
      if (result.priority) {
        setPriority(result.priority);
      }
      if (result.labels && result.labels.length > 0) {
        setLabelsInput(result.labels.join(', '));
      }
      if (result.subtasks && result.subtasks.length > 0) {
        setGeneratedSubtasks(result.subtasks.map((st) => st.title));
      }

      success('AI Decomposition Complete', `Generated ${result.subtasks.length} subtasks & effort estimation.`);
    } catch (err) {
      console.error(err);
    } finally {
      setIsAIBreakdownLoading(false);
    }
  };

  // AI Assignee Recommendation Handler
  const handleAISuggestAssignee = async () => {
    if (!title.trim()) {
      setErrors((prev) => ({ ...prev, title: 'Enter a title first for assignee matching' }));
      return;
    }

    setIsSuggestingAssignee(true);
    try {
      const result = await aiService.suggestAssignee(title, description);

      if (result.recommended_user_id) {
        const found = allUsers.find(
          (u) =>
            u.id === result.recommended_user_id ||
            u.name.toLowerCase().includes(result.recommended_user_name?.toLowerCase() || '')
        );
        if (found) {
          setAssigneeId(found.id);
        }
      }

      setAiAssigneeInfo({
        name: result.recommended_user_name,
        confidence: Math.round(result.confidence * 100),
        reasoning: result.reasoning,
      });

      if (result.suggested_hours && (!estimatedHours || estimatedHours === '8')) {
        setEstimatedHours(String(result.suggested_hours));
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsSuggestingAssignee(false);
    }
  };

  const removeSubtask = (index: number) => {
    setGeneratedSubtasks((prev) => prev.filter((_, idx) => idx !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const newErrors: { title?: string; projectId?: string } = {};

    if (!title.trim()) {
      newErrors.title = 'Task title is required';
    }
    if (!projectId) {
      newErrors.projectId = 'Please select a project';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setIsSubmitting(true);
    try {
      const labels = labelsInput
        .split(',')
        .map((l) => l.trim())
        .filter(Boolean);

      const newTask = await createTask({
        projectId,
        title: title.trim(),
        description: description.trim(),
        status,
        priority,
        assigneeId: assigneeId || undefined,
        creatorId: allUsers[0]?.id || 'user_1',
        dueDate,
        labels: labels.length > 0 ? labels : ['Task'],
        estimatedHours: parseInt(estimatedHours, 10) || 8,
      });

      // Automatically add AI-generated subtasks if any
      if (newTask && generatedSubtasks.length > 0) {
        for (const st of generatedSubtasks) {
          try {
            await addSubtask(newTask.id, st);
          } catch {
            // Ignore subtask add errors
          }
        }
      }

      closeCreateTask();
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isCreateTaskOpen}
      onClose={closeCreateTask}
      title="Create New Task"
      description="Create a task with priority, assignee, milestones, or AI decomposition."
      maxWidth="xl"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Title Input with AI Breakdown Trigger */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="text-xs font-semibold text-[#929AAA]">Task Title *</label>
            <button
              type="button"
              onClick={handleAIBreakdown}
              disabled={isAIBreakdownLoading || !title.trim()}
              className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium bg-[#8B7CFF]/15 hover:bg-[#8B7CFF]/25 border border-[#8B7CFF]/30 text-[#8B7CFF] rounded-lg transition-colors cursor-pointer disabled:opacity-40"
              title="Decomposes requirements into subtasks, hours, and priority"
            >
              {isAIBreakdownLoading ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Decomposing...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>AI Breakdown</span>
                </>
              )}
            </button>
          </div>
          <Input
            placeholder="e.g. Implement real-time WebSocket connection"
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              if (errors.title) setErrors((prev) => ({ ...prev, title: undefined }));
            }}
            error={errors.title}
            autoFocus
          />
        </div>

        <Textarea
          label="Description"
          placeholder="Provide acceptance criteria, notes, or reproduction steps..."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
        />

        {/* AI-Generated Subtasks Section */}
        {generatedSubtasks.length > 0 && (
          <div className="p-3 bg-[#151922] border border-[#8B7CFF]/30 rounded-xl space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-[#8B7CFF] flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" /> Generated Subtasks ({generatedSubtasks.length})
              </span>
              <span className="text-[11px] text-[#929AAA]">Will be created automatically</span>
            </div>
            <div className="space-y-1.5 max-h-36 overflow-y-auto">
              {generatedSubtasks.map((st, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2 rounded-lg bg-[#10131A] border border-[#252B36] text-xs text-[#F5F7FA]"
                >
                  <div className="flex items-center gap-2 truncate">
                    <CheckCircle2 className="w-3.5 h-3.5 text-[#8B7CFF] shrink-0" />
                    <span className="truncate">{st}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeSubtask(idx)}
                    className="text-[#929AAA] hover:text-[#EF4444] p-1 cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Select
            label="Project *"
            value={projectId}
            onChange={(e) => {
              setProjectId(e.target.value);
              if (errors.projectId) setErrors((prev) => ({ ...prev, projectId: undefined }));
            }}
            error={errors.projectId}
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                [{p.key}] {p.name}
              </option>
            ))}
          </Select>

          {/* Assignee with AI Suggest Button */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold text-[#929AAA]">Assignee</label>
              <button
                type="button"
                onClick={handleAISuggestAssignee}
                disabled={isSuggestingAssignee || !title.trim()}
                className="flex items-center gap-1 text-[11px] text-[#8B7CFF] hover:underline cursor-pointer disabled:opacity-40"
              >
                {isSuggestingAssignee ? (
                  <>
                    <RefreshCw className="w-3 h-3 animate-spin" />
                    <span>Matching...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3 h-3" />
                    <span>AI Suggest</span>
                  </>
                )}
              </button>
            </div>
            <Select
              value={assigneeId}
              onChange={(e) => setAssigneeId(e.target.value)}
            >
              <option value="">Unassigned</option>
              {allUsers.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name} ({u.role})
                </option>
              ))}
            </Select>

            {/* AI Reasoning pill */}
            {aiAssigneeInfo && (
              <div className="mt-1.5 p-2 rounded-lg bg-[#151922] border border-[#252B36] flex items-start gap-1.5 text-[11px] text-[#929AAA]">
                <Lightbulb className="w-3.5 h-3.5 text-[#F59E0B] shrink-0 mt-0.5" />
                <div>
                  <span className="text-[#F5F7FA] font-medium">
                    AI Match ({aiAssigneeInfo.confidence}%):{' '}
                  </span>
                  {aiAssigneeInfo.reasoning}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Select
            label="Status"
            value={status}
            onChange={(e) => setStatus(e.target.value as TaskStatus)}
          >
            <option value="backlog">Backlog</option>
            <option value="todo">To Do</option>
            <option value="in_progress">In Progress</option>
            <option value="in_review">In Review</option>
            <option value="done">Done</option>
          </Select>

          <Select
            label="Priority"
            value={priority}
            onChange={(e) => setPriority(e.target.value as Priority)}
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </Select>

          <Input
            label="Due Date"
            type="date"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Input
            label="Labels (comma separated)"
            placeholder="Frontend, Bug, Design..."
            value={labelsInput}
            onChange={(e) => setLabelsInput(e.target.value)}
          />

          <Input
            label="Estimated Hours"
            type="number"
            min="1"
            max="160"
            value={estimatedHours}
            onChange={(e) => setEstimatedHours(e.target.value)}
          />
        </div>

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#252B36]">
          <Button type="button" variant="outline" onClick={closeCreateTask}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" isLoading={isSubmitting}>
            Create Task
          </Button>
        </div>
      </form>
    </Modal>
  );
}

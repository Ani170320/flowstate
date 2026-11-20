'use client';

import React, { useState, useEffect } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Input, Textarea } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useAuth } from '@/context/AuthContext';
import { Priority, TaskStatus } from '@/types';
import { format, addDays } from 'date-fns';

export function CreateTaskModal() {
  const { allUsers } = useAuth();
  const { isCreateTaskOpen, closeCreateTask, defaultProjectId, projects, createTask } = useWorkspace();

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
      setErrors({});
    }
  }, [isCreateTaskOpen, defaultProjectId, projects, allUsers]);

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

      await createTask({
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
      description="Create a task with priority, assignee, and milestones."
      maxWidth="xl"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Task Title *"
          placeholder="e.g. Implement real-time WebSocket connection"
          value={title}
          onChange={(e) => {
            setTitle(e.target.value);
            if (errors.title) setErrors((prev) => ({ ...prev, title: undefined }));
          }}
          error={errors.title}
          autoFocus
        />

        <Textarea
          label="Description"
          placeholder="Provide acceptance criteria, notes, or reproduction steps..."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
        />

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

          <Select
            label="Assignee"
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

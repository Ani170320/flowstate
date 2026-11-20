'use client';

import React, { useState, useEffect } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Input, Textarea } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useAuth } from '@/context/AuthContext';
import { Priority, ProjectStatus } from '@/types';
import { format, addMonths } from 'date-fns';

export function CreateProjectModal() {
  const { allUsers } = useAuth();
  const { isCreateProjectOpen, closeCreateProject, projectToEdit, createProject, updateProject } =
    useWorkspace();

  const isEditing = Boolean(projectToEdit);

  const [name, setName] = useState('');
  const [key, setKey] = useState('');
  const [description, setDescription] = useState('');
  const [status, setStatus] = useState<ProjectStatus>('in_progress');
  const [priority, setPriority] = useState<Priority>('high');
  const [startDate, setStartDate] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [managerId, setManagerId] = useState('');
  const [selectedMemberIds, setSelectedMemberIds] = useState<string[]>([]);
  const [color, setColor] = useState('#8B7CFF');
  const [budget, setBudget] = useState('50000');
  const [tagsInput, setTagsInput] = useState('Product, Engineering');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<{ name?: string; key?: string }>({});

  useEffect(() => {
    if (isCreateProjectOpen) {
      if (projectToEdit) {
        setName(projectToEdit.name);
        setKey(projectToEdit.key);
        setDescription(projectToEdit.description);
        setStatus(projectToEdit.status);
        setPriority(projectToEdit.priority);
        setStartDate(projectToEdit.startDate);
        setDueDate(projectToEdit.dueDate);
        setManagerId(projectToEdit.managerId);
        setSelectedMemberIds(projectToEdit.teamMemberIds || []);
        setColor(projectToEdit.color || '#8B7CFF');
        setBudget(String(projectToEdit.budget || 50000));
        setTagsInput((projectToEdit.tags || []).join(', '));
      } else {
        setName('');
        setKey('');
        setDescription('');
        setStatus('planning');
        setPriority('high');
        setStartDate(format(new Date(), 'yyyy-MM-dd'));
        setDueDate(format(addMonths(new Date(), 2), 'yyyy-MM-dd'));
        setManagerId(allUsers[0]?.id || 'user_1');
        setSelectedMemberIds([allUsers[0]?.id || 'user_1', allUsers[1]?.id || 'user_2']);
        setColor('#8B7CFF');
        setBudget('50000');
        setTagsInput('Engineering, SaaS');
      }
      setErrors({});
    }
  }, [isCreateProjectOpen, projectToEdit, allUsers]);

  const handleNameChange = (val: string) => {
    setName(val);
    if (!isEditing && (!key || key.length <= 4)) {
      // Auto generate 3 letter uppercase key
      const words = val.trim().split(/\s+/);
      const generated =
        words.length >= 2
          ? (words[0][0] + words[1][0] + (words[2] ? words[2][0] : '')).toUpperCase()
          : val.slice(0, 3).toUpperCase();
      setKey(generated);
    }
  };

  const toggleMember = (memberId: string) => {
    setSelectedMemberIds((prev) =>
      prev.includes(memberId) ? prev.filter((id) => id !== memberId) : [...prev, memberId]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const newErrors: { name?: string; key?: string } = {};

    if (!name.trim()) newErrors.name = 'Project name is required';
    if (!key.trim()) newErrors.key = 'Project key identifier is required';

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setIsSubmitting(true);
    try {
      const tags = tagsInput
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);

      if (isEditing && projectToEdit) {
        await updateProject(projectToEdit.id, {
          name: name.trim(),
          key: key.trim().toUpperCase(),
          description: description.trim(),
          status,
          priority,
          startDate,
          dueDate,
          managerId,
          teamMemberIds: selectedMemberIds,
          color,
          budget: parseFloat(budget) || 50000,
          tags,
        });
      } else {
        await createProject({
          name: name.trim(),
          key: key.trim().toUpperCase(),
          description: description.trim(),
          status,
          priority,
          startDate,
          dueDate,
          managerId,
          teamMemberIds: selectedMemberIds,
          color,
          budget: parseFloat(budget) || 50000,
          tags,
        });
      }

      closeCreateProject();
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const projectColors = ['#8B7CFF', '#3B82F6', '#10B981', '#F59E0B', '#EC4899', '#6366F1'];

  return (
    <Modal
      isOpen={isCreateProjectOpen}
      onClose={closeCreateProject}
      title={isEditing ? 'Edit Project' : 'Create New Project'}
      description="Configure workspace roadmaps, timelines, budget, and assigned team members."
      maxWidth="2xl"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-3 gap-4">
          <div className="col-span-2">
            <Input
              label="Project Name *"
              placeholder="e.g. Mobile App v3.0 Rewrite"
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
              error={errors.name}
              autoFocus
            />
          </div>
          <div>
            <Input
              label="Key Identifier *"
              placeholder="e.g. MOB"
              value={key}
              onChange={(e) => setKey(e.target.value.toUpperCase())}
              error={errors.key}
              maxLength={5}
            />
          </div>
        </div>

        <Textarea
          label="Project Description"
          placeholder="Summary of goals, deliverables and scope..."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
        />

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Select
            label="Status"
            value={status}
            onChange={(e) => setStatus(e.target.value as ProjectStatus)}
          >
            <option value="planning">Planning</option>
            <option value="in_progress">In Progress</option>
            <option value="in_review">In Review</option>
            <option value="completed">Completed</option>
            <option value="on_hold">On Hold</option>
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

          <Select
            label="Project Lead"
            value={managerId}
            onChange={(e) => setManagerId(e.target.value)}
          >
            {allUsers.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name} ({u.role})
              </option>
            ))}
          </Select>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Input
            label="Start Date"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
          <Input
            label="Target Due Date"
            type="date"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
          />
        </div>

        {/* Team Members Multi-Select Chips */}
        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-[#929AAA]">
            Assigned Team Members ({selectedMemberIds.length} selected)
          </label>
          <div className="flex flex-wrap gap-2 p-2 bg-[#10131A] border border-[#252B36] rounded-xl max-h-32 overflow-y-auto">
            {allUsers.map((u) => {
              const isSelected = selectedMemberIds.includes(u.id);
              return (
                <button
                  type="button"
                  key={u.id}
                  onClick={() => toggleMember(u.id)}
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-[#8B7CFF]/20 text-[#8B7CFF] border border-[#8B7CFF]/40'
                      : 'bg-[#151922] text-[#929AAA] border border-[#252B36] hover:text-[#F5F7FA]'
                  }`}
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-current" />
                  {u.name}
                </button>
              );
            })}
          </div>
        </div>

        {/* Color Accent Picker & Budget */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-[#929AAA] mb-1.5">Color Accent</label>
            <div className="flex items-center gap-2">
              {projectColors.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setColor(c)}
                  className={`w-7 h-7 rounded-full transition-transform cursor-pointer ${
                    color === c ? 'scale-110 ring-2 ring-white ring-offset-2 ring-offset-[#151922]' : 'opacity-70 hover:opacity-100'
                  }`}
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>
          </div>

          <Input
            label="Budget ($)"
            type="number"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
          />
        </div>

        <Input
          label="Tags (comma separated)"
          placeholder="Design, Security, Mobile, AI..."
          value={tagsInput}
          onChange={(e) => setTagsInput(e.target.value)}
        />

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#252B36]">
          <Button type="button" variant="outline" onClick={closeCreateProject}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" isLoading={isSubmitting}>
            {isEditing ? 'Save Changes' : 'Create Project'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Input, Textarea } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { PriorityBadge, TaskStatusBadge } from '@/components/ui/Badge';
import { Avatar } from '@/components/ui/Avatar';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { TaskStatus, Priority, Comment } from '@/types';
import { taskService } from '@/services/taskService';
import { aiService } from '@/services/aiService';
import {
  Calendar,
  CheckCircle2,
  Circle,
  MessageSquare,
  Plus,
  Trash2,
  Send,
  Clock,
  Tag,
  Share2,
  Paperclip,
  UploadCloud,
  FileText,
  Download,
  Loader2,
  Sparkles,
} from 'lucide-react';
import { formatReadableDate, formatRelativeTime, isTaskOverdue } from '@/lib/utils';

export function TaskDetailModal() {
  const { user, allUsers } = useAuth();
  const { success, error } = useToast();
  const {
    selectedTask,
    closeTaskDetail,
    updateTask,
    deleteTask,
    addSubtask,
    toggleSubtask,
    addComment,
    projects,
  } = useWorkspace();

  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [isEditingDescription, setIsEditingDescription] = useState(false);
  const [newSubtaskTitle, setNewSubtaskTitle] = useState('');
  const [comments, setComments] = useState<Comment[]>([]);
  const [newComment, setNewComment] = useState('');
  const [isLoadingComments, setIsLoadingComments] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isGeneratingSubtasks, setIsGeneratingSubtasks] = useState(false);

  // Attachments State
  const [attachments, setAttachments] = useState<any[]>([]);
  const [isLoadingAttachments, setIsLoadingAttachments] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadAttachments = useCallback(async (taskId: string) => {
    setIsLoadingAttachments(true);
    try {
      const atts = await taskService.getAttachments(taskId);
      setAttachments(Array.isArray(atts) ? atts : []);
    } catch {
      setAttachments([]);
    } finally {
      setIsLoadingAttachments(false);
    }
  }, []);

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0 || !selectedTask) return;
    setIsUploading(true);
    try {
      for (let i = 0; i < files.length; i++) {
        await taskService.uploadAttachment(selectedTask.id, files[i]);
      }
      success('File Uploaded', `${files.length} attachment(s) added successfully.`);
      await loadAttachments(selectedTask.id);
    } catch (err: any) {
      error('Upload Failed', err?.message || 'Could not upload attachment.');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDeleteAttachment = async (attachmentId: string) => {
    if (!selectedTask) return;
    try {
      await taskService.deleteAttachment(attachmentId);
      success('Attachment Deleted', 'File removed from task.');
      await loadAttachments(selectedTask.id);
    } catch (err: any) {
      error('Delete Failed', err?.message || 'Could not delete attachment.');
    }
  };

  const loadComments = useCallback(async (taskId: string) => {
    setIsLoadingComments(true);
    try {
      const c = await taskService.getComments(taskId);
      setComments(c);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoadingComments(false);
    }
  }, []);

  useEffect(() => {
    if (selectedTask) {
      setTitle(selectedTask.title);
      setDescription(selectedTask.description);
      setIsEditingTitle(false);
      setIsEditingDescription(false);
      loadComments(selectedTask.id);
      loadAttachments(selectedTask.id);
    }
  }, [selectedTask, loadComments, loadAttachments]);

  if (!selectedTask) return null;

  const project = projects.find((p) => p.id === selectedTask.projectId);
  const isOverdue = isTaskOverdue(selectedTask.dueDate, selectedTask.status);

  const handleSaveTitle = async () => {
    if (!title.trim() || title === selectedTask.title) {
      setTitle(selectedTask.title);
      setIsEditingTitle(false);
      return;
    }
    await updateTask(selectedTask.id, { title: title.trim() });
    setIsEditingTitle(false);
  };

  const handleSaveDescription = async () => {
    await updateTask(selectedTask.id, { description: description.trim() });
    setIsEditingDescription(false);
  };

  const handleStatusChange = async (status: TaskStatus) => {
    await updateTask(selectedTask.id, { status });
  };

  const handlePriorityChange = async (priority: Priority) => {
    await updateTask(selectedTask.id, { priority });
  };

  const handleAssigneeChange = async (assigneeId: string) => {
    await updateTask(selectedTask.id, { assigneeId: assigneeId || undefined });
  };

  const handleAddSubtask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSubtaskTitle.trim()) return;
    await addSubtask(selectedTask.id, newSubtaskTitle.trim());
    setNewSubtaskTitle('');
  };

  const handleAIGenerateSubtasks = async () => {
    if (!selectedTask) return;
    setIsGeneratingSubtasks(true);
    try {
      const result = await aiService.generateSubtasks(
        selectedTask.title,
        selectedTask.description,
        selectedTask.labels
      );

      if (result.subtasks && result.subtasks.length > 0) {
        for (const st of result.subtasks) {
          await addSubtask(selectedTask.id, st.title);
        }
        success('AI Subtasks Created', `Added ${result.subtasks.length} subtasks to this task.`);
      } else {
        success('Decomposition Complete', 'Task requirements already concise.');
      }
    } catch (err: any) {
      error('AI Error', err?.message || 'Could not generate subtasks.');
    } finally {
      setIsGeneratingSubtasks(false);
    }
  };

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newComment.trim()) return;
    await addComment(selectedTask.id, newComment.trim());
    setNewComment('');
    loadComments(selectedTask.id);
  };

  const handleDelete = async () => {
    if (confirm(`Are you sure you want to delete ${selectedTask.key}?`)) {
      setIsDeleting(true);
      await deleteTask(selectedTask.id);
      setIsDeleting(false);
    }
  };

  const completedSubtasksCount = (selectedTask.subtasks || []).filter((st) => st.completed).length;
  const totalSubtasksCount = (selectedTask.subtasks || []).length;
  const subtaskProgress = totalSubtasksCount > 0 ? Math.round((completedSubtasksCount / totalSubtasksCount) * 100) : 0;

  return (
    <Modal isOpen={Boolean(selectedTask)} onClose={closeTaskDetail} maxWidth="3xl" showCloseButton>
      <div className="space-y-6">
        {/* Header Breadcrumb & Actions */}
        <div className="flex items-center justify-between pb-3 border-b border-[#252B36]">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs px-2 py-0.5 rounded bg-[#10131A] border border-[#252B36] text-[#8B7CFF] font-semibold">
              {selectedTask.key}
            </span>
            <span className="text-xs text-[#929AAA]">{project?.name || selectedTask.projectName}</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                navigator.clipboard.writeText(window.location.href);
                alert('Task link copied to clipboard!');
              }}
              title="Copy task link"
              className="p-1.5 rounded-lg text-[#929AAA] hover:text-[#F5F7FA] hover:bg-[#1B202C] transition-colors cursor-pointer"
            >
              <Share2 className="w-4 h-4" />
            </button>
            <button
              onClick={handleDelete}
              disabled={isDeleting}
              title="Delete task"
              className="p-1.5 rounded-lg text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Title area (editable) */}
        <div>
          {isEditingTitle ? (
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                onBlur={handleSaveTitle}
                onKeyDown={(e) => e.key === 'Enter' && handleSaveTitle()}
                className="w-full text-xl font-bold bg-[#10131A] border border-[#8B7CFF] rounded-lg px-3 py-1.5 text-[#F5F7FA] focus:outline-none"
                autoFocus
              />
              <Button size="sm" onClick={handleSaveTitle}>
                Done
              </Button>
            </div>
          ) : (
            <h2
              onClick={() => setIsEditingTitle(true)}
              className="text-xl font-bold text-[#F5F7FA] tracking-tight hover:bg-[#1B202C]/50 px-2 py-1 -mx-2 rounded-lg cursor-pointer transition-colors"
              title="Click to edit title"
            >
              {selectedTask.title}
            </h2>
          )}
        </div>

        {/* Metadata properties grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3.5 bg-[#10131A] border border-[#252B36] rounded-xl text-xs">
          <div>
            <span className="text-[10px] text-[#929AAA] font-medium uppercase tracking-wider block mb-1">
              Status
            </span>
            <select
              value={selectedTask.status}
              onChange={(e) => handleStatusChange(e.target.value as TaskStatus)}
              className="bg-[#151922] border border-[#252B36] text-[#F5F7FA] rounded-md px-2 py-1 text-xs w-full cursor-pointer focus:outline-none focus:border-[#8B7CFF]"
            >
              <option value="backlog">Backlog</option>
              <option value="todo">To Do</option>
              <option value="in_progress">In Progress</option>
              <option value="in_review">In Review</option>
              <option value="done">Done</option>
            </select>
          </div>

          <div>
            <span className="text-[10px] text-[#929AAA] font-medium uppercase tracking-wider block mb-1">
              Priority
            </span>
            <select
              value={selectedTask.priority}
              onChange={(e) => handlePriorityChange(e.target.value as Priority)}
              className="bg-[#151922] border border-[#252B36] text-[#F5F7FA] rounded-md px-2 py-1 text-xs w-full cursor-pointer focus:outline-none focus:border-[#8B7CFF]"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="urgent">Urgent</option>
            </select>
          </div>

          <div>
            <span className="text-[10px] text-[#929AAA] font-medium uppercase tracking-wider block mb-1">
              Assignee
            </span>
            <select
              value={selectedTask.assigneeId || ''}
              onChange={(e) => handleAssigneeChange(e.target.value)}
              className="bg-[#151922] border border-[#252B36] text-[#F5F7FA] rounded-md px-2 py-1 text-xs w-full cursor-pointer focus:outline-none focus:border-[#8B7CFF]"
            >
              <option value="">Unassigned</option>
              {allUsers.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <span className="text-[10px] text-[#929AAA] font-medium uppercase tracking-wider block mb-1">
              Due Date
            </span>
            <div className="flex items-center gap-1.5 py-1 px-2 bg-[#151922] border border-[#252B36] rounded-md">
              <Calendar className="w-3.5 h-3.5 text-[#929AAA]" />
              <span className={`text-xs ${isOverdue ? 'text-red-400 font-bold' : 'text-[#F5F7FA]'}`}>
                {formatReadableDate(selectedTask.dueDate)}
              </span>
            </div>
          </div>
        </div>

        {/* Labels & Tags */}
        <div className="flex items-center gap-2 flex-wrap">
          <Tag className="w-3.5 h-3.5 text-[#929AAA]" />
          {(selectedTask.labels || []).map((label, idx) => (
            <span
              key={idx}
              className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-[#1B202C] text-[#8B7CFF] border border-[#252B36]"
            >
              {label}
            </span>
          ))}
          {selectedTask.estimatedHours && (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-mono bg-[#10131A] text-[#929AAA] border border-[#252B36]">
              <Clock className="w-3 h-3" />
              {selectedTask.estimatedHours}h est
            </span>
          )}
        </div>

        {/* Description Section */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold text-[#929AAA] uppercase tracking-wider">
              Description
            </h3>
            {!isEditingDescription && (
              <button
                onClick={() => setIsEditingDescription(true)}
                className="text-xs text-[#8B7CFF] hover:underline cursor-pointer"
              >
                Edit
              </button>
            )}
          </div>
          {isEditingDescription ? (
            <div className="space-y-2">
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={4}
                className="w-full bg-[#10131A] border border-[#8B7CFF] rounded-lg p-3 text-sm text-[#F5F7FA] focus:outline-none"
              />
              <div className="flex items-center justify-end gap-2">
                <Button
                  size="xs"
                  variant="outline"
                  onClick={() => {
                    setDescription(selectedTask.description);
                    setIsEditingDescription(false);
                  }}
                >
                  Cancel
                </Button>
                <Button size="xs" variant="primary" onClick={handleSaveDescription}>
                  Save
                </Button>
              </div>
            </div>
          ) : (
            <p
              onClick={() => setIsEditingDescription(true)}
              className="text-sm text-[#F5F7FA]/90 bg-[#10131A]/50 p-3 rounded-xl border border-[#252B36]/60 leading-relaxed cursor-pointer hover:border-[#8B7CFF]/50 transition-colors"
            >
              {selectedTask.description || (
                <span className="text-[#929AAA] italic">Add a description...</span>
              )}
            </p>
          )}
        </div>

        {/* Subtasks Checklist */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-semibold text-[#929AAA] uppercase tracking-wider">
                Subtasks
              </h3>
              <span className="text-xs font-mono text-[#929AAA]">
                ({completedSubtasksCount}/{totalSubtasksCount})
              </span>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleAIGenerateSubtasks}
                disabled={isGeneratingSubtasks}
                className="flex items-center gap-1.5 px-2 py-0.5 text-[11px] font-medium bg-[#8B7CFF]/15 hover:bg-[#8B7CFF]/25 border border-[#8B7CFF]/30 text-[#8B7CFF] rounded-lg transition-colors cursor-pointer disabled:opacity-50"
                title="Automatically generate subtasks with AI"
              >
                {isGeneratingSubtasks ? (
                  <>
                    <Loader2 className="w-3 h-3 animate-spin" />
                    <span>Generating...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3 h-3" />
                    <span>AI Generate</span>
                  </>
                )}
              </button>

              {totalSubtasksCount > 0 && (
                <span className="text-xs font-mono text-[#8B7CFF]">{subtaskProgress}%</span>
              )}
            </div>
          </div>

          {/* Subtask progress bar */}
          {totalSubtasksCount > 0 && (
            <div className="w-full h-1.5 bg-[#1B202C] rounded-full overflow-hidden">
              <div
                className="h-full bg-[#8B7CFF] transition-all duration-300 rounded-full"
                style={{ width: `${subtaskProgress}%` }}
              />
            </div>
          )}

          {/* Subtask items */}
          <div className="space-y-1.5">
            {(selectedTask.subtasks || []).map((st) => (
              <div
                key={st.id}
                onClick={() => toggleSubtask(selectedTask.id, st.id)}
                className="flex items-center gap-2.5 p-2 rounded-lg bg-[#10131A] hover:bg-[#1B202C] border border-[#252B36] cursor-pointer transition-colors"
              >
                {st.completed ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                ) : (
                  <Circle className="w-4 h-4 text-[#929AAA] shrink-0" />
                )}
                <span
                  className={`text-xs flex-1 ${
                    st.completed ? 'line-through text-[#929AAA]' : 'text-[#F5F7FA]'
                  }`}
                >
                  {st.title}
                </span>
              </div>
            ))}
          </div>

          {/* Add Subtask Input */}
          <form onSubmit={handleAddSubtask} className="flex items-center gap-2">
            <input
              type="text"
              placeholder="Add subtask and press Enter..."
              value={newSubtaskTitle}
              onChange={(e) => setNewSubtaskTitle(e.target.value)}
              className="flex-1 bg-[#10131A] border border-[#252B36] rounded-lg px-3 py-1.5 text-xs text-[#F5F7FA] placeholder:text-[#929AAA]/60 focus:outline-none focus:border-[#8B7CFF]"
            />
            <Button type="submit" size="xs" variant="secondary" className="gap-1">
              <Plus className="w-3.5 h-3.5" />
              <span>Add</span>
            </Button>
          </form>
        </div>

        {/* Attachments Section */}
        <div className="space-y-3 pt-3 border-t border-[#252B36]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Paperclip className="w-4 h-4 text-[#8B7CFF]" />
              <h3 className="text-xs font-semibold text-[#929AAA] uppercase tracking-wider">
                Attachments ({attachments.length})
              </h3>
            </div>
            <Button
              type="button"
              size="xs"
              variant="outline"
              disabled={isUploading}
              onClick={() => fileInputRef.current?.click()}
              className="gap-1.5"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Uploading...</span>
                </>
              ) : (
                <>
                  <UploadCloud className="w-3.5 h-3.5" />
                  <span>Upload File</span>
                </>
              )}
            </Button>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => handleFileUpload(e.target.files)}
          />

          {/* Drag & Drop Zone */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragging(false);
              handleFileUpload(e.dataTransfer.files);
            }}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-4 text-center cursor-pointer transition-all ${
              isDragging
                ? 'border-[#8B7CFF] bg-[#8B7CFF]/10'
                : 'border-[#252B36] hover:border-[#8B7CFF]/50 bg-[#10131A]/40'
            }`}
          >
            <div className="flex flex-col items-center justify-center gap-1.5">
              <UploadCloud className={`w-6 h-6 ${isDragging ? 'text-[#8B7CFF]' : 'text-[#929AAA]'}`} />
              <p className="text-xs text-[#F5F7FA]">
                <span className="font-semibold text-[#8B7CFF]">Click to upload</span> or drag and drop files here
              </p>
              <p className="text-[10px] text-[#929AAA]">Images, PDFs, documents, archives</p>
            </div>
          </div>

          {/* Attachments List */}
          {isLoadingAttachments ? (
            <div className="flex items-center justify-center py-4 text-[#929AAA] text-xs">
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
              Loading attachments...
            </div>
          ) : attachments.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {attachments.map((att: any) => (
                <div
                  key={att.id}
                  className="flex items-center justify-between p-2.5 bg-[#10131A] border border-[#252B36] hover:border-[#2E3646] rounded-xl group transition-all"
                >
                  <div className="flex items-center gap-2.5 min-w-0 flex-1">
                    <div className="w-8 h-8 rounded-lg bg-[#1B202C] flex items-center justify-center shrink-0 border border-[#252B36]">
                      <FileText className="w-4 h-4 text-[#8B7CFF]" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium text-[#F5F7FA] truncate" title={att.name}>
                        {att.name}
                      </p>
                      <p className="text-[10px] text-[#929AAA]">
                        {formatFileSize(att.file_size || att.size)} • {formatRelativeTime(att.created_at || att.uploadedAt)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0 ml-2">
                    {att.download_url && (
                      <a
                        href={att.download_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-1 text-[#929AAA] hover:text-[#8B7CFF] rounded transition-colors"
                        title="Download"
                      >
                        <Download className="w-3.5 h-3.5" />
                      </a>
                    )}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteAttachment(att.id);
                      }}
                      className="p-1 text-[#929AAA] hover:text-red-400 rounded transition-colors cursor-pointer"
                      title="Delete"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </div>

        {/* Discussion / Comments Section */}
        <div className="space-y-3 pt-3 border-t border-[#252B36]">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-[#8B7CFF]" />
            <h3 className="text-xs font-semibold text-[#929AAA] uppercase tracking-wider">
              Discussion ({comments.length})
            </h3>
          </div>

          {/* Comment Thread */}
          <div className="space-y-3 max-h-60 overflow-y-auto">
            {comments.map((c) => (
              <div key={c.id} className="flex items-start gap-3 p-3 bg-[#10131A] rounded-xl border border-[#252B36]">
                <Avatar user={c.author} size="sm" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-[#F5F7FA]">{c.author?.name || 'User'}</span>
                    <span className="text-[10px] text-[#929AAA]">
                      {formatRelativeTime(c.createdAt)}
                    </span>
                  </div>
                  <p className="text-xs text-[#929AAA] leading-relaxed">{c.content}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Add Comment Box */}
          <form onSubmit={handleAddComment} className="flex items-center gap-2">
            <Avatar user={user} size="sm" />
            <input
              type="text"
              placeholder="Write a comment or update..."
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              className="flex-1 bg-[#10131A] border border-[#252B36] rounded-lg px-3 py-2 text-xs text-[#F5F7FA] placeholder:text-[#929AAA]/60 focus:outline-none focus:border-[#8B7CFF]"
            />
            <Button type="submit" size="sm" variant="primary" className="cursor-pointer">
              <Send className="w-3.5 h-3.5" />
            </Button>
          </form>
        </div>
      </div>
    </Modal>
  );
}

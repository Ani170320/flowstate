'use client';

import React, { useState, useEffect } from 'react';
import { ProjectFile } from '@/types';
import { projectService } from '@/services/projectService';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { Avatar } from '@/components/ui/Avatar';
import { Button } from '@/components/ui/Button';
import { formatReadableDate } from '@/lib/utils';
import { FileText, FileCode, FileImage, Download, UploadCloud, Plus } from 'lucide-react';

export function ProjectFilesTab({ projectId }: { projectId: string }) {
  const { user } = useAuth();
  const { success } = useToast();
  const [files, setFiles] = useState<ProjectFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    projectService.getProjectFiles(projectId).then(setFiles);
  }, [projectId]);

  const handleSimulatedUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      const uploaded = await projectService.uploadProjectFile(projectId, {
        name: file.name,
        size: file.size,
        type: file.type || 'application/octet-stream',
        userId: user.id,
      });

      setFiles((prev) => [uploaded, ...prev]);
      success('File Attached', `"${file.name}" has been uploaded to project files.`);
    } finally {
      setIsUploading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1048576).toFixed(1)} MB`;
  };

  const getFileIcon = (fileName: string) => {
    if (fileName.endsWith('.pdf')) return <FileText className="w-5 h-5 text-red-400" />;
    if (fileName.endsWith('.json') || fileName.endsWith('.ts') || fileName.endsWith('.js')) {
      return <FileCode className="w-5 h-5 text-amber-400" />;
    }
    if (fileName.endsWith('.png') || fileName.endsWith('.jpg') || fileName.endsWith('.svg')) {
      return <FileImage className="w-5 h-5 text-blue-400" />;
    }
    return <FileText className="w-5 h-5 text-[#8B7CFF]" />;
  };

  return (
    <div className="space-y-5">
      {/* Upload Zone & Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 bg-[#151922] border border-[#252B36] rounded-2xl">
        <div>
          <h3 className="text-sm font-semibold text-[#F5F7FA]">Project Deliverables & Assets</h3>
          <p className="text-xs text-[#929AAA] mt-0.5">
            Specifications, architecture diagrams, compliance audits, and design token exports.
          </p>
        </div>

        <label className="cursor-pointer">
          <input
            type="file"
            className="hidden"
            onChange={handleSimulatedUpload}
            disabled={isUploading}
          />
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-[#8B7CFF] hover:bg-[#7968EE] text-white text-xs font-medium rounded-xl shadow-md shadow-[#8B7CFF]/20 transition-all cursor-pointer">
            <UploadCloud className="w-4 h-4" />
            <span>{isUploading ? 'Uploading...' : 'Upload File'}</span>
          </div>
        </label>
      </div>

      {/* Files Table / List */}
      <div className="bg-[#151922] border border-[#252B36] rounded-2xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-[#252B36] bg-[#10131A]/60 text-[#929AAA] font-medium">
                <th className="py-3 px-4">File Name</th>
                <th className="py-3 px-4 w-28">Size</th>
                <th className="py-3 px-4 w-40">Uploaded By</th>
                <th className="py-3 px-4 w-32">Date</th>
                <th className="py-3 px-4 w-20 text-right">Download</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#252B36]/60">
              {files.map((file) => (
                <tr key={file.id} className="hover:bg-[#10131A]/50 transition-colors">
                  <td className="py-3.5 px-4 font-medium text-[#F5F7FA]">
                    <div className="flex items-center gap-3">
                      {getFileIcon(file.name)}
                      <span className="truncate max-w-xs">{file.name}</span>
                    </div>
                  </td>
                  <td className="py-3.5 px-4 text-[#929AAA] font-mono">
                    {formatFileSize(file.size)}
                  </td>
                  <td className="py-3.5 px-4">
                    <div className="flex items-center gap-2">
                      <Avatar user={file.uploader} size="xs" />
                      <span className="text-[#929AAA] truncate">{file.uploader?.name || 'User'}</span>
                    </div>
                  </td>
                  <td className="py-3.5 px-4 text-[#929AAA] font-mono">
                    {formatReadableDate(file.uploadedAt)}
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <button
                      onClick={() => alert(`Downloading "${file.name}"...`)}
                      className="p-1.5 rounded-lg text-[#929AAA] hover:text-[#8B7CFF] hover:bg-[#10131A] transition-colors cursor-pointer"
                      title="Download file"
                    >
                      <Download className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

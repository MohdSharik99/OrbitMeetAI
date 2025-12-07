import React, { useState, useEffect } from 'react';
import { getAllTranscripts } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
import SearchableSelect from './SearchableSelect';

const ProjectSelector = ({ onSelect, selectedProject, selectedMeeting }) => {
  const { theme } = useTheme();
  const [transcripts, setTranscripts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedProjectKey, setSelectedProjectKey] = useState('');

  useEffect(() => {
    const fetchTranscripts = async () => {
      try {
        setLoading(true);
        const data = await getAllTranscripts();
        setTranscripts(data);
      } catch (err) {
        setError(err.message);
        console.error('Error fetching transcripts:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchTranscripts();
  }, []);

  const projects = transcripts.reduce((acc, transcript) => {
    const projectName = transcript.project_name || 'Unknown Project';
    if (!acc[projectName]) {
      acc[projectName] = {
        project_name: projectName,
        project_key: transcript.project_key,
        project_id: transcript.project_id,
        meetings: [],
      };
    }
    if (transcript.meetings) {
      transcript.meetings.forEach((meeting) => {
        acc[projectName].meetings.push({
          meeting_name: meeting.meeting_name,
          meeting_time: meeting.meeting_time,
        });
      });
    }
    return acc;
  }, {});

  const projectList = Object.values(projects);
  const selectedProjectData = projectList.find(
    (p) => p.project_name === selectedProject
  );
  const meetings = selectedProjectData?.meetings || [];

  const containerBg = theme === 'dark'
    ? 'bg-gray-800/90 border-gray-700'
    : 'bg-white/90 border-gray-200';

  const textColor = theme === 'dark' ? 'text-white' : 'text-black';
  const textSecondary = theme === 'dark' ? 'text-gray-300' : 'text-gray-700';
  const selectBg = theme === 'dark' ? 'bg-gray-700' : 'bg-white';
  const selectBorder = theme === 'dark' ? 'border-gray-600' : 'border-gray-200';

  if (loading) {
    return (
      <div className={`${containerBg} backdrop-blur-sm p-5 rounded-xl shadow-lg border transition-colors duration-300`}>
        <div className={`flex items-center space-x-3 ${textSecondary}`}>
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-[#B56727]"></div>
          <span className="font-semibold text-base">Loading projects...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`${theme === 'dark' ? 'bg-red-900/50' : 'bg-red-50/90'} backdrop-blur-sm border-l-4 border-red-500 p-5 rounded-xl shadow-lg transition-colors duration-300`}>
        <div className="flex items-start space-x-3">
          <svg className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <div className={`${theme === 'dark' ? 'text-red-300' : 'text-red-800'} font-bold mb-1`}>Error loading projects</div>
            <div className={`${theme === 'dark' ? 'text-red-200' : 'text-red-700'} text-sm mb-2`}>{error}</div>
            <div className={`${theme === 'dark' ? 'text-red-300 bg-red-900/30' : 'text-red-600 bg-red-100/50'} text-xs px-2 py-1 rounded inline-block`}>
              Make sure the backend server is running on port 8000
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`${containerBg} backdrop-blur-sm p-5 rounded-xl shadow-lg border transition-colors duration-300`}>
      <div className="flex items-center space-x-3 mb-4">
        <div className="w-10 h-10 bg-[#B56727] rounded-lg flex items-center justify-center shadow-md">
          <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        <h2 className={`text-2xl font-bold ${textColor}`}>Select Project & Meeting</h2>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className={`block text-base font-bold ${textColor} mb-2 flex items-center`}>
            <svg className="w-5 h-5 mr-1.5 text-[#B56727]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
            </svg>
            Project Name
          </label>
          {(() => {
            try {
              if (!projectList || projectList.length === 0) {
                return (
                  <div className={`${selectBg} border-2 ${selectBorder} rounded-xl px-4 py-3 ${textColor}`}>
                    No projects available
                  </div>
                );
              }
              return (
                <SearchableSelect
                  options={projectList}
                  value={selectedProject || ''}
                  onChange={(projectName) => {
                    try {
                      const project = projectList.find((p) => p.project_name === projectName);
                      const projectKey = project?.project_key || '';
                      setSelectedProjectKey(projectKey);
                      onSelect(project?.project_name || '', '', projectKey);
                    } catch (e) {
                      console.error('Error selecting project:', e);
                    }
                  }}
                  placeholder="Search or select a project..."
                  getOptionLabel={(project) => project?.project_name || ''}
                  getOptionValue={(project) => project?.project_name || ''}
                />
              );
            } catch (e) {
              console.error('Error rendering project selector:', e);
              return (
                <select
                  value={selectedProject || ''}
                  onChange={(e) => {
                    const project = projectList.find((p) => p.project_name === e.target.value);
                    const projectKey = project?.project_key || '';
                    setSelectedProjectKey(projectKey);
                    onSelect(project?.project_name || '', '', projectKey);
                  }}
                  className={`w-full px-4 py-3 border-2 ${selectBorder} rounded-xl ${selectBg} ${textColor} font-semibold text-base`}
                >
                  <option value="">Select a project...</option>
                  {projectList.map((project) => (
                    <option key={project.project_name} value={project.project_name}>
                      {project.project_name}
                    </option>
                  ))}
                </select>
              );
            }
          })()}
        </div>

        <div>
          <label className={`block text-base font-bold ${textColor} mb-2 flex items-center`}>
            <svg className="w-5 h-5 mr-1.5 text-[#B56727]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            Meeting Name
          </label>
          {(() => {
            try {
              if (!meetings || meetings.length === 0) {
                return (
                  <div className={`${selectBg} border-2 ${selectBorder} rounded-xl px-4 py-3 ${textColor} ${!selectedProject ? 'opacity-50' : ''}`}>
                    {!selectedProject ? 'Select a project first' : 'No meetings available'}
                  </div>
                );
              }
              return (
                <SearchableSelect
                  options={meetings}
                  value={selectedMeeting || ''}
                  onChange={(meetingName) => {
                    try {
                      const project = projectList.find((p) => p.project_name === selectedProject);
                      const projectKey = project?.project_key || selectedProjectKey;
                      onSelect(selectedProject, meetingName, projectKey);
                    } catch (e) {
                      console.error('Error selecting meeting:', e);
                    }
                  }}
                  placeholder="Search or select a meeting..."
                  disabled={!selectedProject || meetings.length === 0}
                  getOptionLabel={(meeting) => `${meeting?.meeting_name || ''}${meeting?.meeting_time ? ` (${meeting.meeting_time})` : ''}`}
                  getOptionValue={(meeting) => meeting?.meeting_name || ''}
                />
              );
            } catch (e) {
              console.error('Error rendering meeting selector:', e);
              return (
                <select
                  value={selectedMeeting || ''}
                  onChange={(e) => {
                    const project = projectList.find((p) => p.project_name === selectedProject);
                    const projectKey = project?.project_key || selectedProjectKey;
                    onSelect(selectedProject, e.target.value, projectKey);
                  }}
                  disabled={!selectedProject || meetings.length === 0}
                  className={`w-full px-4 py-3 border-2 ${selectBorder} rounded-xl ${selectBg} ${textColor} font-semibold text-base ${
                    theme === 'dark' ? 'disabled:bg-gray-800' : 'disabled:bg-gray-100'
                  }`}
                >
                  <option value="">Select a meeting...</option>
                  {meetings.map((meeting, idx) => (
                    <option key={idx} value={meeting.meeting_name}>
                      {meeting.meeting_name} {meeting.meeting_time ? `(${meeting.meeting_time})` : ''}
                    </option>
                  ))}
                </select>
              );
            }
          })()}
        </div>
      </div>
    </div>
  );
};

export default ProjectSelector;


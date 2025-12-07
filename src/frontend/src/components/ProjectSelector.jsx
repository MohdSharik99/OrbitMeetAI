import React, { useState, useEffect } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import SearchableSelect from './SearchableSelect';
import { getAllTranscripts } from '../services/api';

const ProjectSelector = ({ onSelect, selectedProject, selectedMeeting }) => {
  const { theme } = useTheme();
  const [projectList, setProjectList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedProjectKey, setSelectedProjectKey] = useState('');

  const textColor = theme === 'dark' ? 'text-white' : 'text-black';
  const textSecondary = theme === 'dark' ? 'text-gray-300' : 'text-gray-700';
  const selectBg = theme === 'dark' ? 'bg-gray-800' : 'bg-white';
  const selectBorder = theme === 'dark' ? 'border-gray-600' : 'border-gray-300';

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        setLoading(true);
        setError(null);
        const transcripts = await getAllTranscripts();
        
        if (!transcripts || transcripts.length === 0) {
          setProjectList([]);
          return;
        }

        // Extract unique projects
        const projectsMap = new Map();
        transcripts.forEach((transcript) => {
          // Backend returns lowercase field names: project_name, project_key
          const projectName = transcript.project_name || transcript.Project_name;
          const projectKey = transcript.project_key || transcript.Project_key;
          
          if (!projectName) {
            console.warn('Transcript missing project_name:', transcript);
            return; // Skip transcripts without project name
          }
          
          if (!projectsMap.has(projectName)) {
            projectsMap.set(projectName, {
              project_name: projectName,
              project_key: projectKey || '',
              meetings: []
            });
          }
          
          const project = projectsMap.get(projectName);
          if (transcript.meetings && Array.isArray(transcript.meetings)) {
            transcript.meetings.forEach((meeting) => {
              // Check if meeting already exists to avoid duplicates
              const meetingExists = project.meetings.some(
                m => m.meeting_name === (meeting.meeting_name || meeting.meetingName)
              );
              if (!meetingExists) {
                project.meetings.push({
                  meeting_name: meeting.meeting_name || meeting.meetingName || '',
                  meeting_time: meeting.meeting_time || meeting.meetingTime || ''
                });
              }
            });
          }
        });

        const projects = Array.from(projectsMap.values());
        console.log('Projects loaded:', projects.length, projects);
        if (projects.length > 0) {
          console.log('Sample project structure:', projects[0]);
        }
        setProjectList(projects);
        
        if (projects.length === 0 && transcripts.length > 0) {
          console.warn('No projects extracted from transcripts. Raw data sample:', transcripts[0]);
        }
      } catch (err) {
        console.error('Error fetching projects:', err);
        setError(err.message || 'Failed to load projects');
      } finally {
        setLoading(false);
      }
    };

    fetchProjects();
  }, []);

  // Get meetings for selected project
  const selectedProjectData = projectList.find(
    (p) => p.project_name === selectedProject
  );
  const meetings = selectedProjectData?.meetings || [];

  if (loading) {
    return (
      <div className="flex items-center gap-2 flex-1 min-w-0">
        <div className={`flex items-center space-x-2 ${textSecondary}`}>
          <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-[#B56727]"></div>
          <span className="text-xs font-medium">Loading...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 flex-1 min-w-0">
        <div className={`text-xs ${theme === 'dark' ? 'text-red-300' : 'text-red-800'}`}>
          Error: {error}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 flex-1 min-w-0">
      <div className="flex items-center gap-1.5 flex-1 min-w-0">
        <label className={`text-xs font-bold ${textColor} flex items-center whitespace-nowrap`}>
          Project:
        </label>
        {(() => {
          try {
            if (!projectList || projectList.length === 0) {
              return (
                <div className={`${selectBg} border ${selectBorder} rounded px-2 py-1 ${textColor} text-xs flex-1 min-w-0`}>
                  No projects available
                </div>
              );
            }
            return (
              <div className="flex-1 min-w-0">
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
              </div>
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
                className={`w-full px-2 py-1 border ${selectBorder} rounded ${selectBg} ${textColor} font-medium text-xs flex-1 min-w-0`}
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

      <div className="flex items-center gap-1.5 flex-1 min-w-0">
        <label className={`text-xs font-bold ${textColor} flex items-center whitespace-nowrap`}>
          Meeting:
        </label>
        {(() => {
          try {
            if (!meetings || meetings.length === 0) {
              return (
                <div className={`${selectBg} border ${selectBorder} rounded px-2 py-1 ${textColor} text-xs flex-1 min-w-0 ${!selectedProject ? 'opacity-50' : ''}`}>
                  {!selectedProject ? 'Select a project first' : 'No meetings available'}
                </div>
              );
            }
            return (
              <div className="flex-1 min-w-0">
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
              </div>
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
                className={`w-full px-2 py-1 border ${selectBorder} rounded ${selectBg} ${textColor} font-medium text-xs flex-1 min-w-0 ${
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
  );
};

export default ProjectSelector;

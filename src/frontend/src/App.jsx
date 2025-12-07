import React, { useState, useEffect, useRef } from 'react';
import ProjectSelector from './components/ProjectSelector';
import SummarySection from './components/SummarySection';
import Chatbot from './components/Chatbot';
import ConnectionStatus from './components/ConnectionStatus';
import ThemeToggle from './components/ThemeToggle';
import { getProjectData } from './services/api';
import { useTheme } from './contexts/ThemeContext';

function App() {
  const { theme } = useTheme();
  const [selectedProject, setSelectedProject] = useState('');
  const [selectedMeeting, setSelectedMeeting] = useState('');
  const [projectData, setProjectData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [projectKey, setProjectKey] = useState('');

  // Collapsible chatbot width state (default 20%)
  const [chatbotWidth, setChatbotWidth] = useState(() => {
    const saved = localStorage.getItem('chatbotWidth');
    return saved ? parseFloat(saved) : 20;
  });
  const [isDesktop, setIsDesktop] = useState(window.innerWidth >= 1024);
  const [isChatbotVisible, setIsChatbotVisible] = useState(() => {
    const saved = localStorage.getItem('chatbotVisible');
    return saved ? saved === 'true' : true; // Default to visible
  });
  const [isAnalysisCollapsed, setIsAnalysisCollapsed] = useState(false);
  const [isChatbotCollapsed, setIsChatbotCollapsed] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const resizeRef = useRef(null);

  // Track window size for responsive behavior
  useEffect(() => {
    const handleResize = () => {
      setIsDesktop(window.innerWidth >= 1024);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Save width and visibility to localStorage
  useEffect(() => {
    localStorage.setItem('chatbotWidth', chatbotWidth.toString());
  }, [chatbotWidth]);

  useEffect(() => {
    localStorage.setItem('chatbotVisible', isChatbotVisible.toString());
  }, [isChatbotVisible]);

  // Collapse/expand handlers
  const handleCollapseAnalysis = () => {
    setIsAnalysisCollapsed(true);
    setIsChatbotCollapsed(false);
    setChatbotWidth(95); // Chatbot takes 95% when analysis is collapsed
  };

  const handleCollapseChatbot = () => {
    setIsChatbotCollapsed(true);
    setIsAnalysisCollapsed(false);
    setChatbotWidth(5); // Chatbot takes 5% when collapsed
  };

  const handleExpandBoth = () => {
    setIsAnalysisCollapsed(false);
    setIsChatbotCollapsed(false);
    setChatbotWidth(20); // Reset to default split (20% chatbot, 80% analysis)
  };

  // Handle resize mouse events for draggable separator
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizing || !resizeRef.current) return;

      const container = resizeRef.current.parentElement;
      if (!container) return;

      const containerRect = container.getBoundingClientRect();
      const newWidth = ((containerRect.width - (e.clientX - containerRect.left)) / containerRect.width) * 100;

      // Allow full range: 5% to 95% (allows both sides to take almost full screen)
      const constrainedWidth = Math.max(5, Math.min(95, newWidth));
      setChatbotWidth(constrainedWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing]);

  // Get participants from selected meeting
  const selectedMeetingData = projectData?.meetings?.find(
    (m) => m.meeting_name === selectedMeeting
  );
  const participants = selectedMeetingData?.participants || [];

  // Parse meeting date/time from meeting name or use date_time field
  const getMeetingDateTime = () => {
    if (selectedMeetingData?.date_time) {
      return selectedMeetingData.date_time;
    }
    // Try to parse from meeting name format: "Project Name-20251130_093000"
    const dateMatch = selectedMeeting?.match(/-(\d{8})_(\d{6})/);
    if (dateMatch) {
      const dateStr = dateMatch[1]; // YYYYMMDD
      const timeStr = dateMatch[2]; // HHMMSS
      const year = dateStr.substring(0, 4);
      const month = dateStr.substring(4, 6);
      const day = dateStr.substring(6, 8);
      const hour = timeStr.substring(0, 2);
      const minute = timeStr.substring(2, 4);
      const second = timeStr.substring(4, 6);
      return `${year}-${month}-${day} ${hour}:${minute}:${second}`;
    }
    return null;
  };
  const meetingDateTime = getMeetingDateTime();

  const handleSelect = async (projectName, meetingName, projectKeyValue = '') => {
    setSelectedProject(projectName);
    setSelectedMeeting(meetingName);
    
    // Update projectKey if provided
    if (projectKeyValue) {
      setProjectKey(projectKeyValue);
    }
    
    // Use provided key or existing stored key
    const keyToUse = projectKeyValue || projectKey;
    
    setError(null);

    // Only fetch project data if we have both project name and project key AND a meeting is selected
    if (projectName && keyToUse && meetingName) {
      setProjectData(null); // Clear previous data
      setLoading(true);
      try {
        console.log('Fetching project data with key:', keyToUse);
        const data = await getProjectData(keyToUse);
        console.log('Project data received:', data);
        setProjectData(data);
      } catch (err) {
        console.error('Error fetching project data:', err);
        const errorMessage = err.response?.data?.detail || err.message || 'Failed to load project data. Please try again.';
        setError(errorMessage);
        setProjectData(null);
      } finally {
        setLoading(false);
      }
    } else if (!meetingName) {
      // If no meeting is selected, clear project data
      setProjectData(null);
    } else if (projectName && !keyToUse) {
      // If we have project name but no key, show error
      setError('Project key not found. Please select the project again.');
      setProjectData(null);
    }
  };

  const bgClass = theme === 'dark' 
    ? 'bg-gradient-to-br from-gray-900 via-gray-800 to-black' 
    : 'bg-gradient-to-br from-white via-orange-50 to-white';

  return (
    <div className={`h-screen w-screen overflow-hidden ${bgClass} transition-colors duration-300`}>
      {/* Professional Header - Single Row Compact */}
      <header className={`${theme === 'dark' ? 'bg-gray-900/90 border-gray-700' : 'bg-white/90 border-gray-200'} backdrop-blur-lg shadow-lg border-b sticky top-0 z-50 transition-colors duration-300`}>
        <div className="w-full px-4 py-1.5">
          <div className="flex items-center justify-between gap-3">
            {/* Left: Logo + Title */}
            <div className="flex items-center space-x-2 flex-shrink-0">
              <div className="w-6 h-6 bg-[#B56727] rounded flex items-center justify-center shadow-sm">
                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h1 className={`text-base font-bold ${theme === 'dark' ? 'text-white' : 'text-black'} whitespace-nowrap`}>
                OrbitMeetAI
              </h1>
            </div>
            
            {/* Center: Project and Meeting Selector - Compact */}
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <ProjectSelector
                onSelect={(projectName, meetingName, projectKey) => handleSelect(projectName, meetingName, projectKey)}
                selectedProject={selectedProject}
                selectedMeeting={selectedMeeting}
              />
            </div>
            
            {/* Right: Theme Toggle */}
            <div className="flex items-center space-x-2 flex-shrink-0">
              {/* Chatbot Toggle Button */}
              <button
                onClick={() => setIsChatbotVisible(!isChatbotVisible)}
                className={`px-2 py-1 rounded transition-all flex items-center gap-1.5 ${
                  theme === 'dark'
                    ? isChatbotVisible
                      ? 'bg-[#B56727] text-white hover:bg-[#d17a3a]'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    : isChatbotVisible
                    ? 'bg-[#B56727] text-white hover:bg-[#d17a3a]'
                    : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
                }`}
                title={isChatbotVisible ? 'Hide Chatbot' : 'Show Chatbot'}
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  {isChatbotVisible ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  )}
                </svg>
              </button>
              <ConnectionStatus />
              <ThemeToggle />
            </div>
          </div>
        </div>
      </header>

      {/* Full Screen Main Content */}
      <main className="h-[calc(100vh-40px)] w-full flex flex-col overflow-hidden">
        {/* Error Message */}
        {error && (
          <div className="mx-6 mt-4 mb-2 flex-shrink-0">
            <div className={`${theme === 'dark' ? 'bg-red-900/50 border-red-600 text-red-200' : 'bg-red-50/90 border-red-500 text-red-800'} backdrop-blur-sm border-l-4 px-4 py-3 rounded-lg shadow-md transition-colors duration-300`}>
              <div className="font-semibold mb-1 flex items-center">
                <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                Error
              </div>
              <div className="text-sm">{error}</div>
              {(error.includes('connect') || error.includes('Network')) && (
                <div className={`text-xs mt-2 ${theme === 'dark' ? 'text-red-300 bg-red-900/30' : 'text-red-600 bg-red-100/50'} px-2 py-1 rounded inline-block`}>
                  💡 Make sure the backend server is running: <code className={`${theme === 'dark' ? 'bg-red-800' : 'bg-red-200'} px-1 rounded`}>python -m src.backend.main</code>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="mx-6 mt-4 mb-2 flex-shrink-0">
            <div className={`${theme === 'dark' ? 'bg-gray-800/90 border-gray-700' : 'bg-white/90 border-gray-200'} backdrop-blur-sm p-6 rounded-xl shadow-lg border transition-colors duration-300`}>
              <div className={`flex items-center justify-center space-x-3 ${theme === 'dark' ? 'text-gray-300' : 'text-gray-600'}`}>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-[#B56727]"></div>
                <span className="font-medium">Loading project data...</span>
              </div>
            </div>
          </div>
        )}

        {/* Main Content Area - Full Height Split */}
        {selectedProject ? (
          <div className="flex-1 px-6 pb-6 overflow-hidden flex flex-col min-h-0">
            <div className="flex-1 flex flex-col lg:flex-row min-h-0 gap-6" ref={resizeRef}>
              {/* Left Side - Analysis with Project Selector */}
              <div 
                className={`flex flex-col min-h-0 flex-shrink w-full lg:w-auto transition-all duration-300 ${
                  isAnalysisCollapsed ? 'lg:w-[5%]' : ''
                }`}
                style={{ 
                  width: isDesktop && isChatbotVisible && !isAnalysisCollapsed ? `${100 - chatbotWidth}%` : 
                         isDesktop && isChatbotVisible && isAnalysisCollapsed ? '5%' : '100%',
                  minWidth: isDesktop && isChatbotVisible ? '5%' : '100%'
                }}
              >
                <div className={`${theme === 'dark' ? 'bg-gray-800/90 border-gray-700' : 'bg-white/90 border-gray-200'} backdrop-blur-sm rounded-xl shadow-xl border p-6 h-full flex flex-col overflow-hidden transition-colors duration-300`}>
                  {!selectedMeeting ? (
                    /* No Meeting Selected - Show Message */
                    <div className="flex-1 flex items-center justify-center">
                      <div className="text-center max-w-xl">
                        <div className={`w-20 h-20 mx-auto mb-4 ${theme === 'dark' ? 'bg-[#B56727]/30' : 'bg-[#B56727]/10'} rounded-2xl flex items-center justify-center`}>
                          <svg className="w-10 h-10 text-[#B56727]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                        </div>
                        <h3 className={`text-2xl font-bold ${theme === 'dark' ? 'text-white' : 'text-black'} mb-2`}>
                          Project Selected: {selectedProject}
                        </h3>
                        <p className={`${theme === 'dark' ? 'text-gray-300' : 'text-gray-600'} text-base`}>
                          Please select a meeting from the dropdown above to view analysis.
                        </p>
                      </div>
                    </div>
                  ) : (
                    /* Meeting Selected - Show Analysis */
                    <>
                      <div className="flex items-center justify-between mb-4 flex-shrink-0">
                        <div className="flex items-center gap-4 flex-1 min-w-0">
                          <h2 className={`text-2xl font-bold ${theme === 'dark' ? 'text-white' : 'text-black'} flex items-center whitespace-nowrap`}>
                            <svg className="w-5 h-5 mr-2 text-[#B56727]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                            </svg>
                            Meeting Analysis
                          </h2>
                          {participants.length > 0 && (
                            <div className="flex items-center flex-wrap gap-2 flex-1 min-w-0">
                              <span className={`text-xs font-semibold ${theme === 'dark' ? 'text-gray-300' : 'text-gray-700'} whitespace-nowrap`}>Participants:</span>
                              {participants.map((participant, idx) => (
                                <span
                                  key={idx}
                                  className={`px-2 py-1 rounded-full text-xs font-semibold ${
                                    theme === 'dark' 
                                      ? 'bg-[#B56727]/30 text-white border border-[#B56727]' 
                                      : 'bg-[#B56727]/10 text-[#B56727] border border-[#B56727]'
                                  }`}
                                >
                                  {participant}
                                </span>
                              ))}
                            </div>
                          )}
                          {/* Collapse/Expand Buttons */}
                          {isDesktop && isChatbotVisible && (
                            <div className="flex items-center gap-2 ml-auto">
                              {!isAnalysisCollapsed && !isChatbotCollapsed && (
                                <>
                                  <button
                                    onClick={handleCollapseAnalysis}
                                    className={`px-2 py-1 rounded text-xs font-semibold transition-all ${
                                      theme === 'dark'
                                        ? 'bg-gray-700 text-white hover:bg-gray-600'
                                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                    }`}
                                    title="Collapse Analysis"
                                  >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                    </svg>
                                  </button>
                                  <button
                                    onClick={handleCollapseChatbot}
                                    className={`px-2 py-1 rounded text-xs font-semibold transition-all ${
                                      theme === 'dark'
                                        ? 'bg-gray-700 text-white hover:bg-gray-600'
                                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                    }`}
                                    title="Collapse Chatbot"
                                  >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                                    </svg>
                                  </button>
                                </>
                              )}
                              {(isAnalysisCollapsed || isChatbotCollapsed) && (
                                <button
                                  onClick={handleExpandBoth}
                                  className={`px-2 py-1 rounded text-xs font-semibold transition-all ${
                                    theme === 'dark'
                                      ? 'bg-[#B56727] text-white hover:bg-[#d17a3a]'
                                      : 'bg-[#B56727] text-white hover:bg-[#d17a3a]'
                                  }`}
                                  title="Expand Both"
                                >
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                                  </svg>
                                </button>
                              )}
                            </div>
                          )}
                        </div>
                        {/* Meeting Date and Time - Right side */}
                        {meetingDateTime && (
                          <div className={`flex items-center gap-2 flex-shrink-0 ${theme === 'dark' ? 'text-gray-300' : 'text-gray-600'}`}>
                            <svg className="w-4 h-4 text-[#B56727]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                            <span className="text-xs font-semibold whitespace-nowrap">
                              {new Date(meetingDateTime).toLocaleString('en-US', {
                                year: 'numeric',
                                month: 'long',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                              })}
                            </span>
                          </div>
                        )}
                      </div>
                      <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar min-h-0">
                        {loading ? (
                          <div className="text-center py-12">
                            <div className="flex flex-col items-center space-y-4">
                              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#B56727]"></div>
                              <div className={`${theme === 'dark' ? 'text-gray-300' : 'text-gray-600'} text-base font-medium`}>
                                Loading project data...
                              </div>
                            </div>
                          </div>
                        ) : projectData ? (
                          <SummarySection
                            projectData={projectData}
                            selectedMeeting={selectedMeeting}
                          />
                        ) : (
                          <div className="text-center py-12">
                            <div className={`${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'} text-base`}>
                              No project data available. Please try selecting the project and meeting again.
                            </div>
                          </div>
                        )}
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Draggable Separator Line */}
              {isChatbotVisible && !isAnalysisCollapsed && !isChatbotCollapsed && (
                <div
                  className="hidden lg:block w-1 flex-shrink-0 cursor-col-resize group hover:w-2 transition-all relative"
                  onMouseDown={(e) => {
                    e.preventDefault();
                    setIsResizing(true);
                  }}
                  style={{
                    backgroundColor: isResizing 
                      ? '#B56727' 
                      : theme === 'dark' 
                        ? 'rgba(75, 85, 99, 0.5)' 
                        : 'rgba(209, 213, 219, 0.5)'
                  }}
                >
                  <div className="absolute inset-y-0 left-1/2 transform -translate-x-1/2 w-1 bg-[#B56727] opacity-0 group-hover:opacity-100 transition-opacity"></div>
                  <div className="absolute inset-y-0 -left-2 -right-2 z-10"></div>
                </div>
              )}

              {/* Right Side - Chat - Collapsible Width - Only show when visible */}
              {isChatbotVisible && (
                <div 
                  className={`flex flex-col h-full min-h-0 flex-shrink-0 w-full lg:w-auto transition-all duration-300 ${
                    isChatbotCollapsed ? 'lg:w-[5%]' : ''
                  }`}
                  style={{ 
                    width: isDesktop && !isChatbotCollapsed ? `${chatbotWidth}%` : 
                           isDesktop && isChatbotCollapsed ? '5%' : '100%',
                    minWidth: isDesktop ? '5%' : '100%'
                  }}
                >
                  <Chatbot
                    projectName={selectedProject}
                    meetingName={selectedMeeting}
                  />
                </div>
              )}
            </div>
          </div>
        ) : (
          /* Empty State - Split Layout */
          <div className="flex-1 px-6 pb-6 overflow-hidden flex flex-col min-h-0">
            <div className="flex-1 flex flex-col lg:flex-row min-h-0 gap-6" ref={resizeRef}>
              {/* Left Side - Empty State with Project Selector */}
              <div 
                className={`flex flex-col min-h-0 w-full lg:w-auto flex-shrink transition-all duration-300 ${
                  isAnalysisCollapsed ? 'lg:w-[5%]' : ''
                }`}
                style={{ 
                  width: isDesktop && isChatbotVisible && !isAnalysisCollapsed ? `${100 - chatbotWidth}%` : 
                         isDesktop && isChatbotVisible && isAnalysisCollapsed ? '5%' : '100%'
                }}
              >
                <div className={`${theme === 'dark' ? 'bg-gray-800/90 border-gray-700' : 'bg-white/90 border-gray-200'} backdrop-blur-sm rounded-xl shadow-xl border p-6 h-full flex flex-col transition-colors duration-300`}>
                  <div className="flex-1 flex items-center justify-center">
                    <div className="text-center max-w-xl">
                      <div className={`w-24 h-24 mx-auto mb-6 ${theme === 'dark' ? 'bg-[#B56727]/30' : 'bg-[#B56727]/10'} rounded-2xl flex items-center justify-center`}>
                        <svg className="w-12 h-12 text-[#B56727]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                        </svg>
                      </div>
                      <h3 className={`text-3xl font-bold ${theme === 'dark' ? 'text-white' : 'text-black'} mb-3`}>
                        Welcome to OrbitMeetAI
                      </h3>
                      <p className={`${theme === 'dark' ? 'text-gray-200' : 'text-gray-700'} mb-6 leading-relaxed text-base`}>
                        Select a project and meeting from the dropdown above to begin analyzing your meeting transcripts with AI-powered insights.
                      </p>
                      <div className={`flex items-center justify-center space-x-2 text-sm ${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`}>
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span>Get started by selecting a project above</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Draggable Separator Line */}
              {isChatbotVisible && !isAnalysisCollapsed && !isChatbotCollapsed && (
                <div
                  className="hidden lg:block w-1 flex-shrink-0 cursor-col-resize group hover:w-2 transition-all relative"
                  onMouseDown={(e) => {
                    e.preventDefault();
                    setIsResizing(true);
                  }}
                  style={{
                    backgroundColor: isResizing 
                      ? '#B56727' 
                      : theme === 'dark' 
                        ? 'rgba(75, 85, 99, 0.5)' 
                        : 'rgba(209, 213, 219, 0.5)'
                  }}
                >
                  <div className="absolute inset-y-0 left-1/2 transform -translate-x-1/2 w-1 bg-[#B56727] opacity-0 group-hover:opacity-100 transition-opacity"></div>
                  <div className="absolute inset-y-0 -left-2 -right-2 z-10"></div>
                </div>
              )}

              {/* Right Side - Chat - Collapsible Width - Only show when visible */}
              {isChatbotVisible && (
                <div 
                  className={`flex flex-col h-full min-h-0 w-full lg:w-auto flex-shrink-0 transition-all duration-300 ${
                    isChatbotCollapsed ? 'lg:w-[5%]' : ''
                  }`}
                  style={{ 
                    width: isDesktop && !isChatbotCollapsed ? `${chatbotWidth}%` : 
                           isDesktop && isChatbotCollapsed ? '5%' : '100%',
                    minWidth: isDesktop ? '5%' : '100%'
                  }}
                >
                  <Chatbot
                    projectName={selectedProject}
                    meetingName={selectedMeeting}
                  />
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;


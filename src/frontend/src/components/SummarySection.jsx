import React from 'react';
import { useTheme } from '../contexts/ThemeContext';

const Section = ({ title, children, icon }) => {
  const { theme } = useTheme();

  const containerBg = theme === 'dark'
    ? 'bg-gray-800/80 border-gray-700'
    : 'bg-white/80 border-gray-200';
  
  const contentBg = theme === 'dark'
    ? 'bg-gradient-to-b from-gray-800 to-gray-900'
    : 'bg-gradient-to-b from-white to-gray-50';

  const headerBg = theme === 'dark'
    ? 'bg-[#B56727]'
    : 'bg-[#B56727]';

  return (
    <div className={`${containerBg} backdrop-blur-sm rounded-xl shadow-lg mb-4 overflow-hidden border transition-all`}>
      <div className={`w-full px-6 py-4 flex items-center ${headerBg} text-white shadow-md`}>
        <div className="flex items-center space-x-3">
          {icon}
          <h3 className="text-xl font-bold">{title}</h3>
        </div>
      </div>
      <div className={`p-6 ${contentBg} transition-colors duration-300`}>
        {children}
      </div>
    </div>
  );
};

const SummarySection = ({ projectData, selectedMeeting }) => {
  const { theme } = useTheme();
  
  // Early return if no project data
  if (!projectData) {
    return (
      <div className="text-center py-12">
        <p className={`${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'} text-base`}>
          No project data available.
        </p>
      </div>
    );
  }
  
  // Find the selected meeting data
  const selectedMeetingData = projectData?.meetings?.find(
    (m) => m.meeting_name === selectedMeeting
  );

  // Find participant analysis for the selected meeting
  const participantAnalysis = projectData?.user_analysis?.find(
    (ua) => ua.meeting_name === selectedMeeting
  );

  // Get global summary from project data
  const globalSummary = projectData?.global_summary;

  const textColor = theme === 'dark' ? 'text-white' : 'text-black';
  const textSecondary = theme === 'dark' ? 'text-gray-300' : 'text-gray-700';
  const textTertiary = theme === 'dark' ? 'text-gray-400' : 'text-gray-500';

  const MeetingIcon = (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  );

  const ParticipantsIcon = (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
    </svg>
  );

  const ProjectIcon = (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  );

  // If no meeting is selected, show a message
  if (!selectedMeeting) {
    return (
      <div className="text-center py-12">
        <p className={`${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'} text-base`}>
          Please select a meeting to view its summary.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto pr-2 custom-scrollbar">
      <Section title="Meeting Summary" icon={MeetingIcon}>
        {selectedMeetingData ? (
          <div>
            {selectedMeetingData.summary_points && selectedMeetingData.summary_points.length > 0 ? (
              <ul className="space-y-3">
                {selectedMeetingData.summary_points.map((point, idx) => (
                  <li key={idx} className="flex items-start group">
                    <div className="flex-shrink-0 w-7 h-7 bg-[#B56727] rounded-full flex items-center justify-center mr-3 mt-0.5 shadow-sm">
                      <span className="text-white text-sm font-bold">{idx + 1}</span>
                    </div>
                    <span className={`${textSecondary} text-base leading-relaxed group-hover:${textColor} transition-colors`}>{point}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="text-center py-8">
                <svg className={`w-16 h-16 mx-auto ${textTertiary} mb-3`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className={`${textTertiary} italic text-base`}>No summary points available for this meeting.</p>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-8">
            <svg className={`w-16 h-16 mx-auto ${textTertiary} mb-3`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            <p className={`${textTertiary} italic text-base`}>Please select a meeting to view its summary.</p>
          </div>
        )}
      </Section>

      <Section title="Participant Analysis" icon={ParticipantsIcon}>
        {participantAnalysis ? (
          <div className="space-y-4">
            {participantAnalysis.participant_summaries?.map((participant, idx) => (
              <div key={idx} className={`border-l-4 border-[#B56727] ${
                theme === 'dark' 
                  ? 'bg-gray-700/30' 
                  : 'bg-gray-50'
              } pl-5 py-4 rounded-lg shadow-sm hover:shadow-md transition-all`}>
                <div className="flex items-center mb-3">
                  <div className="w-12 h-12 bg-[#B56727] rounded-full flex items-center justify-center mr-3 shadow-md">
                    <span className="text-white font-bold text-base">
                      {(participant.participant_name || 'U')[0].toUpperCase()}
                    </span>
                  </div>
                  <h4 className={`font-bold ${textColor} text-xl`}>
                    {participant.participant_name || 'Unknown Participant'}
                  </h4>
                </div>
                
                {participant.key_updates && participant.key_updates.length > 0 && (
                  <div className="mb-3">
                    <div className="flex items-center mb-2">
                      <svg className="w-5 h-5 mr-2 text-[#B56727]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span className={`text-base font-bold ${textColor}`}>Key Updates:</span>
                    </div>
                    <ul className={`ml-7 space-y-2 text-base ${textSecondary}`}>
                      {participant.key_updates.map((update, uIdx) => (
                        <li key={uIdx} className="flex items-start">
                          <span className="text-[#B56727] mr-2 mt-1 font-bold">▸</span>
                          <span>{update}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {participant.roadblocks && participant.roadblocks.length > 0 && (
                  <div className="mb-3">
                    <div className="flex items-center mb-2">
                      <svg className="w-5 h-5 mr-2 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                      <span className="text-base font-bold text-red-600">Roadblocks:</span>
                    </div>
                    <ul className={`ml-7 space-y-2 text-base ${textSecondary}`}>
                      {participant.roadblocks.map((block, bIdx) => (
                        <li key={bIdx} className="flex items-start">
                          <span className="text-red-500 mr-2 mt-1 font-bold">▸</span>
                          <span>{block}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {participant.actionable && participant.actionable.length > 0 && (
                  <div>
                    <div className="flex items-center mb-2">
                      <svg className="w-5 h-5 mr-2 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span className="text-base font-bold text-green-600">Action Items:</span>
                    </div>
                    <ul className={`ml-7 space-y-2 text-base ${textSecondary}`}>
                      {participant.actionable.map((action, aIdx) => (
                        <li key={aIdx} className="flex items-start">
                          <span className="text-green-500 mr-2 mt-1 font-bold">▸</span>
                          <span>{action}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <svg className={`w-16 h-16 mx-auto ${textTertiary} mb-3`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
            <p className={`${textTertiary} italic text-base`}>
              {selectedMeeting 
                ? 'No participant analysis available for this meeting.'
                : 'Please select a meeting to view participant analysis.'}
            </p>
          </div>
        )}
      </Section>

      <Section title="Project Summary" icon={ProjectIcon}>
        {globalSummary ? (
          <div className="prose max-w-none">
            <div className={`${textSecondary} leading-relaxed text-base`}>
              {globalSummary.split('\n').map((line, idx) => {
                const trimmed = line.trim();
                
                // Format headers (###, ##, #)
                if (trimmed.startsWith('###')) {
                  return (
                    <h3 key={idx} className={`text-xl font-bold ${textColor} mt-6 mb-3 border-b-2 ${theme === 'dark' ? 'border-gray-600' : 'border-gray-300'} pb-2`}>
                      {trimmed.replace(/^###+\s*/, '')}
                    </h3>
                  );
                }
                if (trimmed.startsWith('##')) {
                  return (
                    <h2 key={idx} className={`text-2xl font-bold ${textColor} mt-6 mb-3 border-b-2 ${theme === 'dark' ? 'border-gray-600' : 'border-gray-300'} pb-2`}>
                      {trimmed.replace(/^##+\s*/, '')}
                    </h2>
                  );
                }
                if (trimmed.startsWith('#')) {
                  return (
                    <h1 key={idx} className={`text-3xl font-bold ${textColor} mt-6 mb-4`}>
                      {trimmed.replace(/^#+\s*/, '')}
                    </h1>
                  );
                }
                
                // Format bold text with **
                if (trimmed.includes('**')) {
                  const parts = trimmed.split(/(\*\*.*?\*\*)/g);
                  return (
                    <p key={idx} className="mb-3 text-base">
                      {parts.map((part, pIdx) => {
                        if (part.startsWith('**') && part.endsWith('**')) {
                          return <strong key={pIdx} className={`font-bold ${textColor} text-lg`}>{part.replace(/\*\*/g, '')}</strong>;
                        }
                        return <span key={pIdx} className={textSecondary}>{part}</span>;
                      })}
                    </p>
                  );
                }
                
                // Format bullet points (- or •)
                if (trimmed.startsWith('- ') || trimmed.startsWith('•') || trimmed.match(/^[-•]\s/)) {
                  return (
                    <div key={idx} className="flex items-start mb-2 ml-2">
                      <span className="text-[#B56727] mr-3 mt-1 font-bold text-lg">•</span>
                      <span className={`flex-1 ${textSecondary} text-base`}>{trimmed.replace(/^[-•]\s*/, '')}</span>
                    </div>
                  );
                }
                
                // Format action items with **Name**: pattern
                if (trimmed.match(/^\*\*.*?\*\*:\s/)) {
                  const match = trimmed.match(/^\*\*(.*?)\*\*:\s*(.*)/);
                  if (match) {
                    return (
                      <div key={idx} className={`mb-3 p-3 ${theme === 'dark' ? 'bg-gray-700/50 border-[#B56727]' : 'bg-gray-100 border-[#B56727]'} rounded-lg border-l-4`}>
                        <strong className={`font-bold text-base ${theme === 'dark' ? 'text-[#d17a3a]' : 'text-[#B56727]'}`}>{match[1]}:</strong>
                        <span className={`ml-2 ${textSecondary} text-base`}>{match[2]}</span>
                      </div>
                    );
                  }
                }
                
                // Regular paragraphs
                if (trimmed) {
                  return (
                    <p key={idx} className={`mb-3 ${textSecondary} text-base leading-relaxed`}>
                      {line}
                    </p>
                  );
                }
                
                // Empty lines - add spacing
                return <div key={idx} className="h-2" />;
              })}
            </div>
          </div>
        ) : (
          <p className={`${textTertiary} italic text-base`}>No global project summary available yet.</p>
        )}
      </Section>
    </div>
  );
};

export default SummarySection;


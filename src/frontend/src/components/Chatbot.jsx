import React, { useState, useRef, useEffect } from 'react';
import { chatWithOrbit } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';

const Chatbot = ({ projectName, meetingName }) => {
  const { theme } = useTheme();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Initialize with welcome message when project/meeting changes
    if (projectName && meetingName) {
      setMessages([{
        role: 'assistant',
        content: `Hello! I'm OrbitMeetAI. I can help you understand the meeting "${meetingName}" from project "${projectName}". What would you like to know?`,
        timestamp: new Date(),
      }]);
    } else {
      setMessages([{
        role: 'assistant',
        content: 'Please select a project and meeting to start chatting.',
        timestamp: new Date(),
      }]);
    }
  }, [projectName, meetingName]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || !projectName || loading) return;

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      // Build chat history for context
      const chatHistory = messages
        .filter((msg) => msg.role !== 'system')
        .map((msg) => ({
          role: msg.role,
          content: msg.content,
        }));

      const response = await chatWithOrbit(projectName, input, chatHistory);

      const assistantMessage = {
        role: 'assistant',
        content: response.answer,
        sources: response.sources || [],
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      let errorMessage = 'Sorry, I encountered an error. Please try again.';
      
      if (error.response) {
        // Server responded with error
        const status = error.response.status;
        const detail = error.response.data?.detail || error.response.data?.message || error.message;
        
        if (status === 404) {
          errorMessage = `Project not found. Please make sure you've selected a valid project.`;
        } else if (status === 500) {
          errorMessage = `Server error: ${detail || 'Please check backend logs and ensure all API keys are configured.'}`;
        } else {
          errorMessage = `Error (${status}): ${detail || error.message}`;
        }
      } else if (error.message) {
        errorMessage = `Error: ${error.message}`;
      }
      
      const errorMsg = {
        role: 'assistant',
        content: errorMessage,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const headerBg = 'bg-[#B56727]';
  
  const containerBg = theme === 'dark'
    ? 'bg-gray-800/90 border-gray-700'
    : 'bg-white/90 border-gray-200';

  const messagesBg = theme === 'dark'
    ? 'bg-gradient-to-b from-gray-800 to-gray-900'
    : 'bg-gradient-to-b from-gray-50 to-white';

  return (
    <div className={`flex flex-col h-full w-full min-h-0 ${containerBg} backdrop-blur-sm rounded-xl shadow-2xl border overflow-hidden transition-colors duration-300`}>
      {/* Professional Chat Header */}
      <div className={`${headerBg} text-white p-3 rounded-t-xl flex-shrink-0`}>
        <div className="flex items-center space-x-2">
          <div className="w-6 h-6 bg-white/20 rounded-lg flex items-center justify-center backdrop-blur-sm">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </div>
          <div className="flex-1">
            <h3 className="font-bold text-base">AI Assistant</h3>
            {projectName && meetingName && (
              <p className="text-xs text-white/90 mt-0.5 font-medium">
                {projectName.length > 20 ? projectName.substring(0, 20) + '...' : projectName}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Messages Area - Fixed scrolling */}
      <div className={`flex-1 overflow-y-auto p-5 space-y-4 custom-scrollbar ${messagesBg} transition-colors duration-300 min-h-0`}>
        {messages.map((message, idx) => (
          <div
            key={idx}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}
          >
            <div
              className={`max-w-[85%] rounded-2xl p-5 shadow-md ${
                message.role === 'user'
                  ? 'bg-[#B56727] text-white'
                  : theme === 'dark'
                  ? 'bg-gray-700 text-white border border-gray-600'
                  : 'bg-white text-black border border-gray-200'
              }`}
            >
              {message.role === 'assistant' && (
                <div className="flex items-center mb-3">
                  <div className="w-7 h-7 bg-[#B56727] rounded-full flex items-center justify-center mr-2">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                  </div>
                  <span className={`text-sm font-bold ${theme === 'dark' ? 'text-gray-200' : 'text-gray-700'}`}>OrbitMeetAI</span>
                </div>
              )}
              <div className={`text-sm leading-relaxed ${theme === 'dark' && message.role === 'assistant' ? 'text-white' : message.role === 'user' ? 'text-white' : 'text-black'}`}>
                {message.role === 'assistant' ? (
                  <div className="prose prose-sm max-w-none">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      rehypePlugins={[rehypeRaw]}
                      components={{
                        p: ({ children }) => <p className={`mb-3 ${message.role === 'user' ? 'text-white' : theme === 'dark' ? 'text-white' : 'text-black'}`}>{children}</p>,
                        strong: ({ children }) => <strong className={`font-bold ${message.role === 'user' ? 'text-white' : theme === 'dark' ? 'text-white' : 'text-black'}`}>{children}</strong>,
                        em: ({ children }) => <em className={`italic ${message.role === 'user' ? 'text-white' : theme === 'dark' ? 'text-white' : 'text-black'}`}>{children}</em>,
                        ul: ({ children }) => <ul className="list-disc list-inside mb-3 space-y-1">{children}</ul>,
                        ol: ({ children }) => <ol className="list-decimal list-inside mb-3 space-y-1">{children}</ol>,
                        li: ({ children }) => <li className="ml-2">{children}</li>,
                        code: ({ children }) => <code className={`px-2 py-1 rounded ${theme === 'dark' ? 'bg-gray-800 text-orange-300' : 'bg-gray-100 text-[#B56727]'} text-sm font-mono`}>{children}</code>,
                        pre: ({ children }) => <pre className={`p-3 rounded-lg mb-3 overflow-x-auto ${theme === 'dark' ? 'bg-gray-800' : 'bg-gray-100'}`}>{children}</pre>,
                        h1: ({ children }) => <h1 className={`text-2xl font-bold mb-2 ${message.role === 'user' ? 'text-white' : theme === 'dark' ? 'text-white' : 'text-black'}`}>{children}</h1>,
                        h2: ({ children }) => <h2 className={`text-xl font-bold mb-2 ${message.role === 'user' ? 'text-white' : theme === 'dark' ? 'text-white' : 'text-black'}`}>{children}</h2>,
                        h3: ({ children }) => <h3 className={`text-lg font-bold mb-2 ${message.role === 'user' ? 'text-white' : theme === 'dark' ? 'text-white' : 'text-black'}`}>{children}</h3>,
                        blockquote: ({ children }) => <blockquote className={`border-l-4 border-[#B56727] pl-4 italic mb-3 ${theme === 'dark' ? 'text-gray-300' : 'text-gray-700'}`}>{children}</blockquote>,
                        a: ({ children, href }) => <a href={href} className="text-[#B56727] underline hover:text-[#d17a3a]" target="_blank" rel="noopener noreferrer">{children}</a>,
                        table: ({ children }) => (
                          <div className="overflow-x-auto mb-3">
                            <table className={`min-w-full border-collapse ${theme === 'dark' ? 'border-gray-600' : 'border-gray-300'}`}>
                              {children}
                            </table>
                          </div>
                        ),
                        thead: ({ children }) => (
                          <thead className={theme === 'dark' ? 'bg-gray-700' : 'bg-gray-100'}>
                            {children}
                          </thead>
                        ),
                        tbody: ({ children }) => <tbody>{children}</tbody>,
                        tr: ({ children }) => (
                          <tr className={`border-b ${theme === 'dark' ? 'border-gray-600' : 'border-gray-300'}`}>
                            {children}
                          </tr>
                        ),
                        th: ({ children }) => (
                          <th className={`px-4 py-2 text-left font-bold ${theme === 'dark' ? 'text-white' : 'text-black'}`}>
                            {children}
                          </th>
                        ),
                        td: ({ children }) => (
                          <td className={`px-4 py-2 ${theme === 'dark' ? 'text-gray-200' : 'text-gray-700'}`}>
                            {children}
                          </td>
                        ),
                        br: () => <br />,
                      }}
                    >
                      {message.content}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <p>{message.content}</p>
                )}
              </div>
              {message.sources && message.sources.length > 0 && (
                <div className={`mt-3 pt-3 border-t ${theme === 'dark' ? 'border-gray-600' : 'border-gray-300'}`}>
                  <div className="flex items-start">
                    <svg className={`w-4 h-4 mr-1.5 mt-0.5 ${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                    </svg>
                    <div>
                      <p className={`text-sm font-bold mb-1 ${theme === 'dark' ? 'text-gray-200' : 'text-gray-700'}`}>Sources:</p>
                      <p className={`text-sm leading-relaxed ${theme === 'dark' ? 'text-gray-300' : 'text-gray-600'}`}>
                        {message.sources.join(', ')}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className={`${theme === 'dark' ? 'bg-gray-700 border-gray-600' : 'bg-white border-gray-200'} rounded-2xl p-4 shadow-md border`}>
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-[#B56727] rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-[#d17a3a] rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-[#9a551f] rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <span className={`text-sm ml-2 font-medium ${theme === 'dark' ? 'text-gray-200' : 'text-gray-700'}`}>Thinking...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Professional Input Area */}
      <form onSubmit={handleSend} className={`border-t ${theme === 'dark' ? 'border-gray-700 bg-gray-800/50' : 'border-gray-200 bg-white/50'} backdrop-blur-sm p-4 flex-shrink-0 transition-colors duration-300`}>
        <div className="flex space-x-3">
          <div className="flex-1 relative">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={projectName ? "Ask a question about the meeting..." : "Select project and meeting first"}
              disabled={!projectName || loading}
              className={`w-full px-4 py-3 pr-12 border-2 rounded-xl focus:ring-2 focus:ring-[#B56727] focus:border-[#B56727] disabled:cursor-not-allowed transition-all shadow-sm text-lg ${
                theme === 'dark' 
                  ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400 disabled:bg-gray-800' 
                  : 'bg-white border-gray-200 text-black placeholder-gray-400 disabled:bg-gray-100'
              }`}
            />
            <svg className={`absolute right-4 top-1/2 transform -translate-y-1/2 w-5 h-5 ${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <button
            type="submit"
            disabled={!input.trim() || !projectName || loading}
            className="px-6 py-3 bg-[#B56727] text-white rounded-xl hover:bg-[#9a551f] disabled:bg-gray-400 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-xl font-bold flex items-center space-x-2"
          >
            <span>Send</span>
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </form>
    </div>
  );
};

export default Chatbot;


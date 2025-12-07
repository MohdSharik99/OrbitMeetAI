import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { useTheme } from '../contexts/ThemeContext';

const ConnectionStatus = () => {
  const { theme } = useTheme();
  const [status, setStatus] = useState('checking');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const checkConnection = async () => {
      try {
        const response = await api.get('/health');
        if (response.data.status === 'ok') {
          setStatus('connected');
          setMessage('Backend connected');
        } else {
          setStatus('error');
          setMessage('Backend not ready');
        }
      } catch (error) {
        setStatus('error');
        setMessage('Cannot connect to backend');
      }
    };

    checkConnection();
    // Check every 5 seconds
    const interval = setInterval(checkConnection, 5000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = () => {
    switch (status) {
      case 'connected':
        return 'bg-green-500';
      case 'error':
        return 'bg-red-500';
      default:
        return 'bg-yellow-500';
    }
  };

  const containerBg = theme === 'dark'
    ? 'bg-gray-800/80 border-gray-700'
    : 'bg-white/80 border-gray-200';
  
  const textColor = theme === 'dark' ? 'text-gray-200' : 'text-gray-700';

  return (
    <div className={`flex items-center space-x-3 ${containerBg} backdrop-blur-sm px-4 py-2 rounded-lg shadow-md border transition-colors duration-300`}>
      <div className="relative">
        <div className={`w-3 h-3 rounded-full ${getStatusColor()} animate-pulse`}></div>
        <div className={`absolute inset-0 w-3 h-3 rounded-full ${getStatusColor()} animate-ping opacity-75`}></div>
      </div>
      <span className={`text-sm font-semibold ${textColor}`}>{message}</span>
    </div>
  );
};

export default ConnectionStatus;


import React, { useState, useRef, useEffect } from 'react';
import { useTheme } from '../contexts/ThemeContext';

const SearchableSelect = ({
  options = [],
  value,
  onChange,
  placeholder = 'Select...',
  disabled = false,
  getOptionLabel,
  getOptionValue,
  className = '',
}) => {
  const { theme } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const dropdownRef = useRef(null);
  const inputRef = useRef(null);

  // Validate required functions
  if (!getOptionLabel || !getOptionValue) {
    console.error('SearchableSelect: getOptionLabel and getOptionValue are required');
    return (
      <div className="p-4 border border-red-500 rounded text-red-500">
        Error: SearchableSelect requires getOptionLabel and getOptionValue props
      </div>
    );
  }

  const selectBg = theme === 'dark' ? 'bg-gray-700' : 'bg-white';
  const selectBorder = theme === 'dark' ? 'border-gray-600' : 'border-gray-200';
  const textColor = theme === 'dark' ? 'text-white' : 'text-black';
  const hoverBg = theme === 'dark' ? 'hover:bg-gray-600' : 'hover:bg-gray-100';

  // Safely get selected option
  const selectedOption = Array.isArray(options) && options.length > 0
    ? options.find(opt => {
        try {
          return getOptionValue(opt) === value;
        } catch (e) {
          console.error('Error getting option value:', e);
          return false;
        }
      })
    : null;
  
  const displayValue = selectedOption 
    ? (() => {
        try {
          return getOptionLabel(selectedOption);
        } catch (e) {
          console.error('Error getting option label:', e);
          return '';
        }
      })()
    : '';

  // Filter options based on search term
  const filteredOptions = Array.isArray(options) ? options.filter(opt => {
    try {
      const label = getOptionLabel(opt).toLowerCase();
      return label.includes(searchTerm.toLowerCase());
    } catch (e) {
      console.error('Error filtering option:', e);
      return false;
    }
  }) : [];

  // Debug: Log options when dropdown opens
  useEffect(() => {
    if (isOpen) {
      console.log('SearchableSelect dropdown opened');
      console.log('Options count:', options.length);
      console.log('Filtered options count:', filteredOptions.length);
      console.log('Search term:', searchTerm);
      if (options.length > 0) {
        console.log('First option:', options[0]);
      }
    }
  }, [isOpen, options, filteredOptions, searchTerm]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
        setSearchTerm('');
        setHighlightedIndex(-1);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handle keyboard navigation
  const handleKeyDown = (e) => {
    if (disabled) return;

    if (e.key === 'Enter') {
      e.preventDefault();
      if (highlightedIndex >= 0 && filteredOptions[highlightedIndex]) {
        handleSelect(filteredOptions[highlightedIndex]);
      } else if (isOpen) {
        setIsOpen(false);
      } else {
        setIsOpen(true);
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (!isOpen) {
        setIsOpen(true);
      } else {
        setHighlightedIndex(prev => 
          prev < filteredOptions.length - 1 ? prev + 1 : prev
        );
      }
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightedIndex(prev => prev > 0 ? prev - 1 : 0);
    } else if (e.key === 'Escape') {
      setIsOpen(false);
      setSearchTerm('');
      setHighlightedIndex(-1);
    }
  };

  const handleSelect = (option) => {
    try {
      const optionValue = getOptionValue(option);
      onChange(optionValue);
      setIsOpen(false);
      setSearchTerm('');
      setHighlightedIndex(-1);
    } catch (e) {
      console.error('Error selecting option:', e);
    }
  };

  const handleInputChange = (e) => {
    const value = e.target.value;
    setSearchTerm(value);
    setHighlightedIndex(-1);
    if (!isOpen) {
      setIsOpen(true);
    }
  };

  const handleFocus = () => {
    if (!disabled) {
      setIsOpen(true);
      setSearchTerm(''); // Clear search term when focusing
    }
  };

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      <div
        className={`w-full px-2 py-1 border ${selectBorder} rounded focus-within:ring-1 focus-within:ring-[#B56727] focus-within:border-[#B56727] ${selectBg} ${textColor} shadow-sm transition-all font-bold text-xs ${
          disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
        } ${isOpen ? 'ring-1 ring-[#B56727] border-[#B56727]' : ''}`}
        onClick={() => !disabled && setIsOpen(!isOpen)}
      >
        <div className="flex items-center justify-between">
          <input
            ref={inputRef}
            type="text"
            value={isOpen ? searchTerm : displayValue}
            onChange={handleInputChange}
            onFocus={handleFocus}
            onKeyDown={handleKeyDown}
            placeholder={isOpen ? 'Type to search...' : placeholder}
            disabled={disabled}
            className={`flex-1 bg-transparent border-none outline-none ${textColor} placeholder-gray-400 text-xs`}
            readOnly={!isOpen}
          />
          <svg
            className={`w-3.5 h-3.5 transition-transform ${isOpen ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {isOpen && !disabled && (
        <div className={`absolute z-[9999] w-full mt-1 ${selectBg} border ${selectBorder} rounded shadow-2xl max-h-60 overflow-y-auto custom-scrollbar`}>
          {filteredOptions.length > 0 ? (
            <ul className="py-2">
              {filteredOptions.map((option, index) => {
                try {
                  const optionValue = getOptionValue(option);
                  const optionLabel = getOptionLabel(option);
                  const isSelected = optionValue === value;
                  const isHighlighted = index === highlightedIndex;

                  return (
                    <li
                      key={optionValue || index}
                      onClick={() => handleSelect(option)}
                      className={`px-2 py-1.5 cursor-pointer transition-colors text-xs ${
                        isSelected
                          ? 'bg-[#B56727] text-white'
                          : isHighlighted
                          ? `${theme === 'dark' ? 'bg-gray-600' : 'bg-gray-100'} ${textColor}`
                          : `${textColor} ${hoverBg}`
                      }`}
                      onMouseEnter={() => setHighlightedIndex(index)}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold truncate">{optionLabel}</span>
                        {isSelected && (
                          <svg className="w-4 h-4 flex-shrink-0 ml-2" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                        )}
                      </div>
                    </li>
                  );
                } catch (e) {
                  console.error('Error rendering option:', e, option);
                  return null;
                }
              })}
            </ul>
          ) : (
            <div className={`px-2 py-4 text-center text-xs ${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`}>
              No options found
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SearchableSelect;

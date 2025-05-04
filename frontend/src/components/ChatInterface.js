import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './ChatInterface.css';

const ChatInterface = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const formatTime = (date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const processResponse = (response) => {
    // Initialize sections with default values
    const sections = {
      itinerary: '',
      flights: [],
      hotels: []
    };

    if (!response) return sections;

    // Split by newlines and process each line
    const lines = response.split('\n');
    let currentSection = 'itinerary';

    for (let line of lines) {
      if (line.includes('Flight options')) {
        currentSection = 'flights';
        continue;
      } else if (line.includes('Hotel options')) {
        currentSection = 'hotels';
        continue;
      }

      if (currentSection === 'itinerary') {
        if (!line.includes('Flight options') && !line.includes('Hotel options')) {
          sections.itinerary += line + '\n';
        }
      } else if (currentSection === 'flights' && line.trim()) {
        const flightMatch = line.match(/(\d+)\.\s+(.*?)\s+[-–]\s+\$(.*?)\s+.*?Duration:\s+(.*?)\s+.*?Departs:\s+(.*?)\s+.*?Arrives:\s+(.*?)\s+.*?\[Book here\]\((.*?)\)/);
        if (flightMatch) {
          sections.flights.push({
            airline: flightMatch[2].trim(),
            price: flightMatch[3].trim(),
            duration: flightMatch[4].trim(),
            departure: flightMatch[5].trim(),
            arrival: flightMatch[6].trim(),
            bookingLink: flightMatch[7].trim()
          });
        }
      } else if (currentSection === 'hotels' && line.trim()) {
        const hotelMatch = line.match(/(\d+)\.\s+(.*?)\s+\((\d+)\s+stars?\)\s+[-–]\s+(.*?)\s+(.*?)\s+.*?\[Book here\]\((.*?)\)/);
        if (hotelMatch) {
          sections.hotels.push({
            name: hotelMatch[2].trim(),
            stars: hotelMatch[3].trim(),
            price: hotelMatch[4].trim(),
            currency: hotelMatch[5].trim(),
            bookingLink: hotelMatch[6].trim()
          });
        }
      }
    }

    sections.itinerary = sections.itinerary.trim();
    return sections;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const timestamp = new Date();
    const userMessage = {
      text: input,
      sender: 'user',
      timestamp: timestamp,
      status: 'sent'
    };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await axios.post('http://localhost:8000/api/chat', {
        message: input
      });

      const sections = processResponse(response.data.response);
      const botMessage = {
        text: sections,
        sender: 'bot',
        timestamp: new Date(),
        status: 'read'
      };
      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('Error:', error);
      const errorMessage = {
        text: 'Sorry, there was an error processing your request.',
        sender: 'bot',
        timestamp: new Date(),
        status: 'read'
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const renderMessage = (message) => {
    const timeString = formatTime(message.timestamp);

    if (message.sender === 'user') {
      return (
        <div className="message user">
          <div className="message-content">
            <p>{message.text}</p>
            <div className="message-meta">
              <span className="time">{timeString}</span>
              {message.status === 'sent' && <span className="status">✓</span>}
              {message.status === 'read' && <span className="status read">✓✓</span>}
            </div>
          </div>
        </div>
      );
    } else {
      const sections = typeof message.text === 'object' ? message.text : {
        itinerary: message.text || '',
        flights: [],
        hotels: []
      };

      return (
        <div className="message bot">
          <div className="message-content">
            {sections.itinerary && sections.itinerary.trim() && (
              <div className="itinerary-section">
                <h3>Your Itinerary</h3>
                <div className="itinerary-content">
                  {sections.itinerary.split('\n').map((line, index) => (
                    <p key={index}>{line}</p>
                  ))}
                </div>
              </div>
            )}

            {Array.isArray(sections.flights) && sections.flights.length > 0 && (
              <div className="flights-section">
                <h3>Flight Options</h3>
                <div className="cards-container">
                  {sections.flights.map((flight, index) => (
                    <div key={index} className="card flight-card">
                      <div className="card-header">
                        <h4>{flight.airline}</h4>
                        <span className="price">${flight.price}</span>
                      </div>
                      <div className="card-body">
                        <p><span className="icon">🕐</span> {flight.duration}</p>
                        <p><span className="icon">🛫</span> {flight.departure}</p>
                        <p><span className="icon">🛬</span> {flight.arrival}</p>
                      </div>
                      <div className="card-footer">
                        <a href={flight.bookingLink} target="_blank" rel="noopener noreferrer" className="book-button">
                          Book Flight
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {Array.isArray(sections.hotels) && sections.hotels.length > 0 && (
              <div className="hotels-section">
                <h3>Hotel Options</h3>
                <div className="cards-container">
                  {sections.hotels.map((hotel, index) => (
                    <div key={index} className="card hotel-card">
                      <div className="card-header">
                        <h4>{hotel.name}</h4>
                        <span className="stars">{'⭐'.repeat(parseInt(hotel.stars))}</span>
                      </div>
                      <div className="card-body">
                        <p className="price">{hotel.price} {hotel.currency}</p>
                      </div>
                      <div className="card-footer">
                        <a href={hotel.bookingLink} target="_blank" rel="noopener noreferrer" className="book-button">
                          Book Hotel
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div className="message-meta">
              <span className="time">{timeString}</span>
            </div>
          </div>
        </div>
      );
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.map((message, index) => (
          <div key={index} className="message-container">
            {renderMessage(message)}
          </div>
        ))}
        {isLoading && (
          <div className="message bot">
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <form onSubmit={handleSubmit} className="chat-input-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about travel plans..."
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading}>
          Send
        </button>
      </form>
    </div>
  );
};

export default ChatInterface; 
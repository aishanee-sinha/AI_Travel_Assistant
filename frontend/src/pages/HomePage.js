import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import './HomePage.css';

const HomePage = () => {
    const [activeFeature, setActiveFeature] = useState(0);
    const features = [
        {
            icon: '✈️',
            title: 'Flight Planning',
            description: 'Find the best flights and compare prices',
            color: '#3498db'
        },
        {
            icon: '🏨',
            title: 'Hotel Recommendations',
            description: 'Discover the perfect place to stay',
            color: '#e74c3c'
        },
        {
            icon: '🌤️',
            title: 'Weather Updates',
            description: 'Get accurate weather forecasts for your destination',
            color: '#2ecc71'
        },
        {
            icon: '📅',
            title: 'Itinerary Planning',
            description: 'Create detailed travel plans and schedules',
            color: '#f1c40f'
        }
    ];

    useEffect(() => {
        const interval = setInterval(() => {
            setActiveFeature((prev) => (prev + 1) % features.length);
        }, 3000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="home-container">
            <div className="background-animation"></div>

            <header className="header">
                <h1 className="title">AI Travel Assistant</h1>
                <p className="subtitle">Your personal travel planning companion</p>
            </header>

            <section className="features">
                {features.map((feature, index) => (
                    <div
                        key={index}
                        className={`feature-card ${index === activeFeature ? 'active' : ''}`}
                        style={{ '--card-color': feature.color }}
                        onMouseEnter={() => setActiveFeature(index)}
                    >
                        <div className="feature-icon">{feature.icon}</div>
                        <h3>{feature.title}</h3>
                        <p>{feature.description}</p>
                    </div>
                ))}
            </section>

            <div className="cta-section">
                <Link to="/chat" className="start-chat-button">
                    <span>Start Planning Your Trip</span>
                    <div className="button-arrow">→</div>
                </Link>
            </div>

            <div className="floating-elements">
                <div className="floating-element element-1">✈️</div>
                <div className="floating-element element-2">🏨</div>
                <div className="floating-element element-3">🌍</div>
                <div className="floating-element element-4">🗺️</div>
            </div>
        </div>
    );
};

export default HomePage; 
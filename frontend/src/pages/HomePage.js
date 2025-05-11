import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import './HomePage.css';

<<<<<<< Updated upstream
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
=======
const features = [
    {
        icon: '✈️',
        title: 'Flight Planning',
        description: 'Find the best flights and compare prices',
        color: '#3498db',
        stop: 0.15
    },
    {
        icon: '🏨',
        title: 'Hotel Recommendations',
        description: 'Discover the perfect place to stay',
        color: '#e74c3c',
        stop: 0.4
    },
    {
        icon: '🌤️',
        title: 'Weather Updates',
        description: 'Get accurate weather forecasts for your destination',
        color: '#2ecc71',
        stop: 0.65
    },
    {
        icon: '📅',
        title: 'Itinerary Planning',
        description: 'Create detailed travel plans and schedules',
        color: '#f1c40f',
        stop: 0.9
    }
];

const PATH_LENGTH = 1; // SVG path length (normalized)

function getPointAt(pathRef, t) {
    if (!pathRef.current) return { x: 0, y: 0 };
    const path = pathRef.current;
    const len = path.getTotalLength();
    return path.getPointAtLength(t * len);
}

const HomePage = () => {
    const [activeFeature, setActiveFeature] = useState(0);
    const [planeT, setPlaneT] = useState(0);
    const pathRef = React.useRef(null);
>>>>>>> Stashed changes

    useEffect(() => {
        const interval = setInterval(() => {
            setActiveFeature((prev) => (prev + 1) % features.length);
<<<<<<< Updated upstream
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
=======
        }, 3500);
        return () => clearInterval(interval);
    }, []);

    // Animate plane along the path
    useEffect(() => {
        let frame;
        let t = 0;
        function animate() {
            t += 0.0025;
            if (t > PATH_LENGTH) t = 0;
            setPlaneT(t);
            frame = requestAnimationFrame(animate);
        }
        frame = requestAnimationFrame(animate);
        return () => cancelAnimationFrame(frame);
    }, []);

    // Get plane position
    const planePos = getPointAt(pathRef, planeT);

    return (
        <div className="home-hero">
            {/* Sticky Auth Buttons */}
            <div className="global-auth-buttons sticky-auth">
                <Link to="/login" className="auth-button login">Sign In</Link>
                <Link to="/signup" className="auth-button signup">Sign Up</Link>
            </div>
            {/* Animated Background Elements */}
            <div className="background-animations">
                <div className="cloud cloud-1" />
                <div className="cloud cloud-2" />
            </div>
            {/* Hero Content */}
            <div className="hero-center travel-path-hero">
                <h1 className="hero-title">AI Travel Assistant</h1>
                <p className="hero-subtitle">Your personal travel planning companion</p>
                <div className="travel-path-container" style={{ position: 'relative' }}>
                    <svg className="travel-path-svg" viewBox="0 0 800 320" width="100%" height="320">
                        <path
                            ref={pathRef}
                            d="M 80 260 Q 250 60 400 160 Q 550 260 720 80"
                            stroke="#6e7ff3"
                            strokeDasharray="8 8"
                            strokeWidth="5"
                            fill="none"
                        />
                        {/* Feature stops */}
                        {features.map((feature, idx) => {
                            const pt = getPointAt(pathRef, feature.stop);
                            return (
                                <g key={idx} style={{ cursor: 'pointer' }} onMouseEnter={() => setActiveFeature(idx)}>
                                    <circle cx={pt.x} cy={pt.y} r="32" fill="#fff" stroke={feature.color} strokeWidth="4" filter={idx === activeFeature ? 'drop-shadow(0 0 12px #6e7ff3)' : ''} />
                                    <text x={pt.x} y={pt.y + 8} textAnchor="middle" fontSize="2rem" style={{ pointerEvents: 'none' }}>{feature.icon}</text>
                                </g>
                            );
                        })}
                        {/* Animated plane */}
                        <g style={{ pointerEvents: 'none' }}>
                            <circle cx={planePos.x} cy={planePos.y} r="18" fill="#fff" opacity="0.7" />
                            <text x={planePos.x} y={planePos.y + 8} textAnchor="middle" fontSize="1.5rem">✈️</text>
                        </g>
                    </svg>
                </div>
                {/* Place CTA Button as a block element centered below the animation */}
                <Link to="/chat" className="start-chat-button modular-glow" style={{ display: 'block', margin: '2.5rem auto 0 auto' }}>
>>>>>>> Stashed changes
                    <span>Start Planning Your Trip</span>
                    <div className="button-arrow">→</div>
                </Link>
            </div>
<<<<<<< Updated upstream

            <div className="floating-elements">
                <div className="floating-element element-1">✈️</div>
                <div className="floating-element element-2">🏨</div>
                <div className="floating-element element-3">🌍</div>
                <div className="floating-element element-4">🗺️</div>
            </div>
=======
>>>>>>> Stashed changes
        </div>
    );
};

export default HomePage; 
import React from 'react';
import './ItineraryDay.css';

const getActivityIcon = (activity) => {
    const lowerActivity = activity.toLowerCase();
    if (lowerActivity.includes('breakfast') || lowerActivity.includes('lunch') || lowerActivity.includes('dinner')) return '🍽️';
    if (lowerActivity.includes('museum') || lowerActivity.includes('gallery')) return '🏛️';
    if (lowerActivity.includes('park') || lowerActivity.includes('garden')) return '🌳';
    if (lowerActivity.includes('shopping')) return '🛍️';
    if (lowerActivity.includes('beach')) return '🏖️';
    if (lowerActivity.includes('night') || lowerActivity.includes('evening')) return '🌙';
    if (lowerActivity.includes('morning')) return '🌅';
    if (lowerActivity.includes('tour')) return '🚶';
    if (lowerActivity.includes('airport') || lowerActivity.includes('flight')) return '✈️';
    return '📍';
};

const ItineraryDay = ({ dayNumber, dayLabel, activities }) => {
    return (
        <div className="itinerary-day fade-in-timeline">
            <div className="day-header">
                <div className="day-number-container">
                    <span className="day-number">{dayNumber ? `Day ${dayNumber}` : '🗓️'}</span>
                </div>
                <div className="day-title-container">
                    <span className="day-title">{dayLabel || 'Itinerary'}</span>
                </div>
            </div>
            <div className="activities-list">
                {activities.map((activity, idx) => (
                    <div key={idx} className="activity-item">
                        <span className="activity-icon">{getActivityIcon(activity)}</span>
                        <span className="activity-text">{activity}</span>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default ItineraryDay; 
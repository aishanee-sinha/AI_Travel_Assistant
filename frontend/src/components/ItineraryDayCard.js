import React from 'react';
import './ItineraryDayCard.css';

const ItineraryDayCard = ({ day, activities }) => {
    const getActivityIcon = (activity) => {
        const lowerActivity = activity.toLowerCase();
        if (lowerActivity.includes('breakfast') || lowerActivity.includes('lunch') || lowerActivity.includes('dinner')) {
            return '🍽️';
        } else if (lowerActivity.includes('museum') || lowerActivity.includes('gallery')) {
            return '🏛️';
        } else if (lowerActivity.includes('park') || lowerActivity.includes('garden')) {
            return '🌳';
        } else if (lowerActivity.includes('shopping')) {
            return '🛍️';
        } else if (lowerActivity.includes('beach')) {
            return '🏖️';
        } else if (lowerActivity.includes('night') || lowerActivity.includes('evening')) {
            return '🌙';
        } else {
            return '📍';
        }
    };

    return (
        <div className="itinerary-day-card fade-in">
            <div className="day-header">
                <div className="day-number">Day {day}</div>
                <div className="day-line"></div>
            </div>

            <div className="activities-list">
                {activities.map((activity, index) => (
                    <div key={index} className="activity-item">
                        <div className="activity-icon">{getActivityIcon(activity)}</div>
                        <div className="activity-content">
                            <div className="activity-text">{activity}</div>
                            {index < activities.length - 1 && <div className="activity-connector"></div>}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default ItineraryDayCard; 
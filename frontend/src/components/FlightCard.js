import React from 'react';
import './FlightCard.css';

const FlightCard = ({ flight }) => {
    // Extract flight details using regex
    const airline = flight.match(/Airline: (.*?)(?:\n|$)/)?.[1] || 'N/A';
    const departure = flight.match(/From: (.*?)(?:\n|$)/)?.[1] || 'N/A';
    const arrival = flight.match(/To: (.*?)(?:\n|$)/)?.[1] || 'N/A';
    const time = flight.match(/Time: (.*?)(?:\n|$)/)?.[1] || 'N/A';
    const price = flight.match(/Price: (.*?)(?:\n|$)/)?.[1] || 'N/A';
    const bookingLink = flight.match(/(https?:\/\/[^\s]+)/)?.[0];

    return (
        <div className="flight-card fade-in">
            <div className="flight-header">
                <div className="airline-info">
                    <span className="airline-icon">✈️</span>
                    <span className="airline-name">{airline}</span>
                </div>
                <div className="flight-price">{price}</div>
            </div>

            <div className="flight-route">
                <div className="route-point departure">
                    <div className="city">{departure}</div>
                    <div className="time">{time.split(' - ')[0]}</div>
                </div>

                <div className="route-line">
                    <div className="plane-icon">✈️</div>
                </div>

                <div className="route-point arrival">
                    <div className="city">{arrival}</div>
                    <div className="time">{time.split(' - ')[1]}</div>
                </div>
            </div>

            {bookingLink && (
                <div className="flight-footer">
                    <a
                        href={bookingLink}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="book-button"
                    >
                        Book Now
                    </a>
                </div>
            )}
        </div>
    );
};

export default FlightCard; 
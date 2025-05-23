import React from 'react';
import './HotelCard.css';

const HotelCard = ({ hotel }) => {
    // Extract hotel details using regex
    // const name = hotel.match(/Hotel: (.*?)(?:\n|$)/)?.[1] || 'N/A';
    const location = hotel.match(/Location: (.*?)(?:\n|$)/)?.[1] || 'N/A';
    // const rating = hotel.match(/Rating: (.*?)(?:\n|$)/)?.[1] || 'N/A';
    // const price = hotel.match(/Price: (.*?)(?:\n|$)/)?.[1] || 'N/A';
    const amenities = hotel.match(/Amenities: (.*?)(?:\n|$)/)?.[1]?.split(', ') || [];
    // const bookingLink = hotel.match(/(https?:\/\/[^\s]+)/)?.[0];

    const name = hotel.match(/^(.*?)(?:\s\(\d+\sstars\))/)?.[1] || 'N/A';
    const rating = hotel.match(/\((\d+)\sstars\)/)?.[1] || 'N/A';
    const price = hotel.match(/-\s([\d.,]+)\sUSD/)?.[1] || 'N/A';
    const bookingLink = hotel.match(/Link:\s(https?:\/\/[^\s]+)/)?.[1];

    const getRatingStars = (rating) => {
        const numRating = parseFloat(rating);
        return '⭐'.repeat(Math.floor(numRating));
    };

    return (
        <div className="hotel-card fade-in">
            <div className="hotel-header">
                <div className="hotel-name">{name}</div>
                <div className="hotel-rating">
                    {getRatingStars(rating)}
                    <span className="rating-text">{rating}</span>
                </div>
            </div>
            

            <div className="hotel-footer">
                <div className="hotel-price">${price}</div>
                {bookingLink && (
                    <a
                        href={bookingLink}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="book-button"
                    >
                        Book Now
                    </a>
                )}
            </div>
        </div>
    );
};

export default HotelCard; 
import React from 'react';
import { jsPDF } from 'jspdf';
import 'jspdf-autotable';

const ItineraryPDF = ({ itineraryData }) => {
  const generatePDF = () => {
    const doc = new jsPDF();
    
    // Add title
    doc.setFontSize(20);
    doc.text('Your Travel Itinerary', 20, 20);
    
    // Add dateg
    doc.setFontSize(12);
    doc.text(`Generated on: ${new Date().toLocaleDateString()}`, 20, 30);
    
    // Process itinerary data
    const lines = itineraryData.replace(/[\u{0080}-\u{FFFF}]/gu,"").split('\n');
    let yPosition = 40;
    
    lines.forEach(line => {
      if (line.trim()) {
        // Check if it's a day header
        if (line.includes('Day')) {
          doc.setFontSize(16);
          doc.setFont(undefined, 'bold');
          yPosition += 10;
        } else if (line.includes('Morning') || line.includes('Afternoon') || line.includes('Evening')) {
          doc.setFontSize(14);
          doc.setFont(undefined, 'bold');
          yPosition += 8;
        } else {
          doc.setFontSize(12);
          doc.setFont(undefined, 'normal');
        }
        
        // Add text with word wrap
        const splitText = doc.splitTextToSize(line, 170);
        doc.text(splitText, 20, yPosition);
        yPosition += splitText.length * 7;
        
        // Add new page if needed
        if (yPosition > 270) {
          doc.addPage();
          yPosition = 20;
        }
      }
    });
    
    // Save the PDF
    doc.save('travel-itinerary.pdf');
  };

  return (
    <button 
      onClick={generatePDF}
      className="download-pdf-button"
      style={{
        padding: '10px 20px',
        backgroundColor: '#4CAF50',
        color: 'white',
        border: 'none',
        borderRadius: '5px',
        cursor: 'pointer',
        fontSize: '14px',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        margin: '10px 0'
      }}
    >
      📄 Download Itinerary PDF
    </button>
  );
};

export default ItineraryPDF; 
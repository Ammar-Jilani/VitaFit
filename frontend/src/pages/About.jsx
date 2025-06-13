import React from 'react';
import './About.css';

function About() {
  return (
    <section className="about-page">
      <div className="about-overlay">
        <div className="about-content">
          <h1>About <span>VitaFit</span></h1>
          <p>
            <strong>VitaFit</strong> is your intelligent fitness companion, combining the power of AI and cloud technology to revolutionize health tracking. 
            When you're snapping a photo of your meal, VitaFit analyzes it instantly and gives you personalized feedback. <strong>Note:</strong> Currently limited to only five food classification (Burger, Donut, Fried-Chicken, Hotdog and Pizza).
          </p>
          <p>
            With real-time calorie estimation, personalized fitness recommendations, and beautiful health reports, VitaFit helps you stay on track without the hassle of manual logging. 
            It's a lightweight, modular, cloud-native solution designed to fit effortlessly into your life.
          </p>
          <p>
            Say goodbye to generic apps; and welcome a smart, adaptive approach to your health journey.
          </p>
        </div>
      </div>
    </section>
  );
}

export default About;

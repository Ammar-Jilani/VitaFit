// frontend/src/pages/FitnessPlanner.jsx
import React, { useState, useEffect } from 'react';
import './FitnessPlanner.css';
import { v4 as uuidv4 } from 'uuid';
import AIChat from '../components/AIChat'; // Import the new AI Chat component

function FitnessPlanner() {
    // Hardcoded Backend Base URL (replace with your actual AWS Public IP)
    const BACKEND_BASE_URL = "http://13.214.177.16:8000";

    const [submitted, setSubmitted] = useState(false); // True after initial exercise prediction
    const [sessionId, setSessionId] = useState(''); // State to store the session ID
    const [exercisePlan, setExercisePlan] = useState(null); // State for exercise predictions
    const [dietPlan, setDietPlan] = useState(null); // State for diet predictions
    const [loadingPredictions, setLoadingPredictions] = useState(false); // Loading state for API call (for exercise)
    const [loadingDietPlan, setLoadingDietPlan] = useState(false); // New loading state for diet plan API call
    const [predictionError, setPredictionError] = useState(''); // Error state for initial prediction (exercise)
    const [dietPredictionError, setDietPredictionError] = useState(''); // Error state for diet prediction

    const [formData, setFormData] = useState({
        name: '',
        mobile: '',
        email: '',
        age: '',
        gender: '',
        heightValue: '',
        heightUnit: 'cm',
        weightValue: '',
        weightUnit: 'kg',
        bmi: '', // auto-calculated
        caloriesIntake: '',
    });

    // Effect to calculate BMI
    useEffect(() => {
        const heightValue = parseFloat(formData.heightValue);
        const weightValue = parseFloat(formData.weightValue);

        if (isNaN(heightValue) || isNaN(weightValue) || heightValue <= 0 || weightValue <= 0) {
            setFormData((prev) => ({ ...prev, bmi: '' }));
            return;
        }

        let heightInMeters;
        if (formData.heightUnit === 'cm') {
            heightInMeters = heightValue / 100;
        } else if (formData.heightUnit === 'inches') {
            heightInMeters = (heightValue * 2.54) / 100;
        } else if (formData.heightUnit === 'feet') {
            heightInMeters = (heightValue * 30.48) / 100;
        } else {
            heightInMeters = 0; // Should not happen with current options
        }

        let weightInKg;
        if (formData.weightUnit === 'kg') {
            weightInKg = weightValue;
        } else if (formData.weightUnit === 'lbs') {
            weightInKg = weightValue * 0.453592;
        } else {
            weightInKg = 0; // Should not happen with current options
        }

        if (heightInMeters > 0 && weightInKg > 0) {
            const bmiValue = (weightInKg / (heightInMeters * heightInMeters)).toFixed(2);
            setFormData((prev) => ({ ...prev, bmi: bmiValue }));
        } else {
            setFormData((prev) => ({ ...prev, bmi: '' }));
        }
    }, [formData.heightValue, formData.heightUnit, formData.weightValue, formData.weightUnit]);

    // Generate session ID on component mount
    useEffect(() => {
        setSessionId(uuidv4());
    }, []);

    const validateForm = () => {
        const { name, mobile, email, age, gender, heightValue, heightUnit, weightValue, weightUnit, caloriesIntake } = formData;

        // --- Existing Validations (Basic checks for empty/invalid input) ---
        if (!name.trim()) {
            setPredictionError('Full Name is required.');
            return false;
        }
        if (!mobile.trim()) {
            setPredictionError('Mobile Number is required.');
            return false;
        }
        if (!/^\d+$/.test(mobile.trim())) {
            setPredictionError('Mobile Number should only contain digits.');
            return false;
        }
        if (!email.trim()) {
            setPredictionError('Email is required.');
            return false;
        }

        // --- Age Validation ---
        const ageNum = parseInt(age);
        if (!age || isNaN(ageNum) || ageNum <= 0) {
            setPredictionError('Age must be a valid positive number.');
            return false;
        }
        if (ageNum < 3) {
            setPredictionError("How are you even typing?!?💀");
            return false;
        }
        if (ageNum > 130) {
            setPredictionError("Bro, you're not that old!");
            return false;
        }

        if (!gender) {
            setPredictionError('Gender is required.');
            return false;
        }

        // --- Height Validation ---
        const heightNum = parseFloat(heightValue);
        if (!heightValue || isNaN(heightNum) || heightNum <= 0) {
            setPredictionError('Height must be a valid positive number.');
            return false;
        }

        let heightInCm;
        if (heightUnit === 'cm') {
            heightInCm = heightNum;
        } else if (heightUnit === 'inches') {
            heightInCm = heightNum * 2.54;
        } else if (heightUnit === 'feet') {
            heightInCm = heightNum * 30.48;
        }

        if (heightInCm < 30) {
            setPredictionError("An elf?!");
            return false;
        }
        if (heightInCm > 250) {
            setPredictionError("Burj Khalifa?");
            return false;
        }

        // --- Weight Validation ---
        const weightNum = parseFloat(weightValue);
        if (!weightValue || isNaN(weightNum) || weightNum <= 0) {
            setPredictionError('Weight must be a valid positive number.');
            return false;
        }

        let weightInKg;
        if (weightUnit === 'kg') {
            weightInKg = weightNum;
        } else if (weightUnit === 'lbs') {
            weightInKg = weightNum * 0.453592;
        }

        if (weightInKg < 10) { // Very low weight
            setPredictionError("Are you sure you're not a feather?");
            return false;
        }
        if (weightInKg > 500) { // Very high weight
            setPredictionError("How fat are you?!?");
            return false;
        }

        if (!caloriesIntake || isNaN(parseInt(caloriesIntake)) || parseInt(caloriesIntake) <= 0) {
            setPredictionError('Daily Calorie Intake must be a valid positive number.');
            return false;
        }

        setPredictionError(''); // Clear any previous errors if all checks pass
        return true;
    };

    const handleInitialSubmit = async (e) => {
        e.preventDefault();

        if (!validateForm()) {
            return; // Stop if validation fails
        }

        setLoadingPredictions(true);
        setPredictionError('');
        setDietPredictionError(''); // Clear diet error too

        const dataToSend = {
            session_id: sessionId,
            age: parseInt(formData.age),
            gender: formData.gender,
            height_value: parseFloat(formData.heightValue),
            height_unit: formData.heightUnit,
            weight_value: parseFloat(formData.weightValue),
            weight_unit: formData.weightUnit,
            calories_intake: parseInt(formData.caloriesIntake),
        };

        try {
            const response = await fetch(`${BACKEND_BASE_URL}/predict_exercise`, { // Updated URL
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(dataToSend),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Failed to get exercise plan. Please check your inputs.");
            }

            const result = await response.json();
            console.log("Exercise prediction response:", result);
            setExercisePlan(result.exercise_plan);
            setDietPlan(null); // Reset diet plan for a new session/initial submission
            setSubmitted(true); // Indicate initial submission is complete
        } catch (error) {
            console.error("Exercise prediction error:", error.message);
            setPredictionError(error.message);
        } finally {
            setLoadingPredictions(false);
        }
    };

    const handleDietPrediction = async () => {
        setLoadingDietPlan(true);
        setDietPredictionError('');

        const dietDataToSend = {
            session_id: sessionId,
        };

        try {
            const response = await fetch(`${BACKEND_BASE_URL}/predict_diet`, { // Updated URL
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(dietDataToSend),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Failed to get diet plan. Please try again.");
            }

            const result = await response.json();
            console.log("Diet prediction response:", result);
            setDietPlan(result.diet_plan);
        } catch (error) {
            console.error("Diet prediction error:", error.message);
            setDietPredictionError(error.message);
        } finally {
            setLoadingDietPlan(false);
        }
    };


    const handleDownloadReport = async () => {
        try {
            const userDetails = {
                first_name: formData.name.split(' ')[0] || '',
                last_name: formData.name.split(' ').slice(1).join(' ') || '',
                email: formData.email,
                phone: formData.mobile,
            };

            const response = await fetch(`${BACKEND_BASE_URL}/generate_report`, { // Updated URL
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    user_details: userDetails
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Failed to generate report. Please try again later.");
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(new Blob([blob]));
            const link = document.createElement('a');
            link.href = url;
            const contentDisposition = response.headers.get('Content-Disposition');
            const filenameMatch = contentDisposition && contentDisposition.match(/filename="([^"]+)"/);
            const filename = filenameMatch ? filenameMatch[1] : `Fitness_Report_${sessionId}.pdf`;

            link.setAttribute('download', filename);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error("Report download error:", error.message);
            // Optionally, add a state for report download error message
            // setReportDownloadError(error.message);
            alert(`Error downloading report: ${error.message}`); // Simple alert for now
        }
    };

    const handleChange = (e) => {
        const { name, value } = e.target;

        let newValue = value;
        if (name === 'mobile') {
            // Filter out non-digit characters
            newValue = value.replace(/\D/g, '');
        }

        setFormData((prev) => ({
            ...prev,
            [name]: newValue,
        }));
    };

    return (
        <div className="fitness-bg">
            <div className="main-content-wrapper"> {/* New wrapper for main content and chat */}
                <div className="form-and-reports-area"> {/* Existing form-overlay content */}
                    {!submitted ? (
                        <>
                            <h1 className="fade-text">Enter Your Details for Fitness Suggestions</h1>
                            <form className="fitness-form" onSubmit={handleInitialSubmit}>
                                <input
                                    type="text"
                                    name="name"
                                    placeholder="👤 Full Name"
                                    value={formData.name}
                                    onChange={handleChange}
                                    required
                                />
                                <input
                                    type="tel" // Keep type="tel" for mobile keyboard accessibility
                                    name="mobile"
                                    placeholder="📞 Mobile Number"
                                    value={formData.mobile}
                                    onChange={handleChange}
                                    required
                                />
                                <input
                                    type="email"
                                    name="email"
                                    placeholder="📧 Email"
                                    value={formData.email}
                                    onChange={handleChange}
                                    required
                                />
                                <input
                                    type="number"
                                    name="age"
                                    placeholder="🎂 Age"
                                    value={formData.age}
                                    onChange={handleChange}
                                    required
                                />
                                <select
                                    name="gender"
                                    value={formData.gender}
                                    onChange={handleChange}
                                    required
                                >
                                    <option value="">⚧️ Select Gender</option>
                                    <option value="male">♂️ Male</option>
                                    <option value="female">♀️ Female</option>
                                </select>

                                {/* Height Input with Unit Selection */}
                                <div className="input-group">
                                    <input
                                        type="number"
                                        name="heightValue"
                                        placeholder="📏 Height"
                                        value={formData.heightValue}
                                        onChange={handleChange}
                                        required
                                    />
                                    <select
                                        name="heightUnit"
                                        value={formData.heightUnit}
                                        onChange={handleChange}
                                        className="unit-select"
                                    >
                                        <option value="cm">cm</option>
                                        <option value="inches">inches</option>
                                        <option value="feet">feet</option>
                                    </select>
                                </div>

                                {/* Weight Input with Unit Selection */}
                                <div className="input-group">
                                    <input
                                        type="number"
                                        name="weightValue"
                                        placeholder="⚖️ Weight"
                                        value={formData.weightValue}
                                        onChange={handleChange}
                                        required
                                    />
                                    <select
                                        name="weightUnit"
                                        value={formData.weightUnit}
                                        onChange={handleChange}
                                        className="unit-select"
                                    >
                                        <option value="kg">kg</option>
                                        <option value="lbs">lbs</option>
                                    </select>
                                </div>

                                <input
                                    type="number"
                                    name="caloriesIntake"
                                    placeholder="🍎 Daily Calorie Intake (e.g., 2000)"
                                    value={formData.caloriesIntake}
                                    onChange={handleChange}
                                    required
                                />
                                {/* BMI Display - Changed from input to div */}
                                <div className="bmi-display">
                                    <span>📊 BMI: </span>
                                    {formData.bmi ? <strong>{formData.bmi}</strong> : 'Auto-calculated'}
                                </div>
                                <button type="submit" className="animated-btn" disabled={loadingPredictions}>
                                    {loadingPredictions ? 'Processing...' : '✅ Get Exercise Plan'}
                                </button>
                                {predictionError && <p className="error-message">{predictionError}</p>}
                            </form>
                        </>
                    ) : ( // After initial submission
                        <div className="report-container-wrapper"> {/* Renamed from report-and-chat-container to clarify purpose */}
                            {/* Container for the side-by-side reports */}
                            <div className="reports-container">
                                {/* Exercise Report Section */}
                                <div className="recommendation-report">
                                    <h2>Daily Exercise Recommendation Report</h2>
                                    {exercisePlan ? (
                                        <table className="fitness-table">
                                            <thead>
                                                <tr>
                                                    <th>🏃‍♂️ Exercise Type</th>
                                                    <th>🔥 Intensity</th>
                                                    <th>📅 Frequency</th>
                                                    <th>⏱️ Duration</th>
                                                    <th>⚡ Calorie Burn</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr>
                                                    <td>{exercisePlan.exercise_type}</td>
                                                    <td>{exercisePlan.intensity_level}</td>
                                                    <td>{exercisePlan.frequency_per_week} times/week</td>
                                                    <td>{exercisePlan.duration_minutes} mins/session</td>
                                                    <td>{exercisePlan.estimated_calorie_burn} kcal/session</td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    ) : (
                                        <p>No exercise plan available.</p>
                                    )}
                                </div>

                                {/* Diet Plan Display - Only show if dietPlan exists */}
                                {dietPlan && (
                                    <div className="recommendation-report diet-plan slide-in">
                                        <h2>VitaFit Suggested Diet Plan</h2>
                                        {!dietPlan.error && (
                                            <table className="fitness-table">
                                                <thead>
                                                    <tr>
                                                        <th>🍽️ Calories/Day</th>
                                                        <th>🥩 Protein (g)</th>
                                                        <th>🍞 Carbs (g)</th>
                                                        <th>🥑 Fats (g)</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td>{dietPlan.recommended_calories} kcal</td>
                                                        <td>{dietPlan.protein_grams_per_day} g</td>
                                                        <td>{dietPlan.carbs_grams_per_day} g</td>
                                                        <td>{dietPlan.fats_grams_per_day} g</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        )}
                                        {dietPlan.error && <p className="error-message">{dietPlan.error}</p>}
                                        {dietPlan.message && <p className="info-message">{dietPlan.message}</p>}
                                    </div>
                                )}
                            </div> {/* End reports-container */}

                            {/* New section for Diet Plan Button and related text - positioned in the middle */}
                            {submitted && !dietPlan && (
                                <div className="diet-plan-prompt">
                                    <p>Ready for a personalized diet plan?</p>
                                    <button
                                        className="animated-btn"
                                        onClick={handleDietPrediction}
                                        disabled={loadingDietPlan}
                                    >
                                        {loadingDietPlan ? 'Generating Diet Plan...' : 'Generate Diet Plan'}
                                    </button>
                                    {dietPredictionError && <p className="error-message">{dietPredictionError}</p>}
                                </div>
                            )}

                            {/* Download Report button is now below both plans (or the diet plan prompt if diet plan is not generated) */}
                            {/* This button will always show after initial submission */}
                            {submitted && (
                                <div className="final-report-download">
                                    <h2>Download your complete fitness report now!</h2>
                                    <button className="animated-btn" onClick={handleDownloadReport}>
                                        Download Overall Fitness Report (PDF)
                                    </button>
                                </div>
                            )}
                        </div>
                    )}
                </div> {/* End form-and-reports-area */}

                {/* Integrate the AI Chat component here, outside of the form-overlay/reports structure */}
                {submitted && ( // Only show AI chat after initial submission
                    <div className="ai-chat-sidebar"> {/* Renamed for clarity - this will be the right sidebar */}
                        <AIChat BACKEND_BASE_URL={BACKEND_BASE_URL} sessionId={sessionId} />
                    </div>
                )}
            </div> {/* End main-content-wrapper */}
        </div>
    );
}

export default FitnessPlanner;

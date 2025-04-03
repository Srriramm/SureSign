import React, { useState, useRef } from 'react';
import Webcam from 'react-webcam';
import './WebcamCapture.css';

const WebcamCapture = ({ onCapture }) => {
  const webcamRef = useRef(null);
  const [image, setImage] = useState(null);
  const [isCameraActive, setIsCameraActive] = useState(true);

  const capture = () => {
    const imageSrc = webcamRef.current.getScreenshot();
    setImage(imageSrc);
    onCapture(imageSrc);
    setIsCameraActive(false);
  };

  const retake = () => {
    setImage(null);
    onCapture(null);  // Clear the image in parent component
    setIsCameraActive(true);
  };

  const videoConstraints = {
    width: 400,
    height: 400,
    facingMode: "user"
  };

  return (
    <div className="webcam-container">
      {isCameraActive ? (
        <>
          <Webcam
            audio={false}
            ref={webcamRef}
            screenshotFormat="image/jpeg"
            videoConstraints={videoConstraints}
            className="webcam"
          />
          <div className="webcam-overlay">
            <div className="face-outline"></div>
          </div>
          <div className="capture-instructions">
            <p>Please position your face within the circle</p>
            <button type="button" className="capture-button" onClick={capture}>Capture Photo</button>
          </div>
        </>
      ) : (
        <div className="captured-image-container">
          <img src={image} alt="Captured selfie" className="captured-image" />
          <button type="button" className="retake-button" onClick={retake}>Retake Photo</button>
        </div>
      )}
    </div>
  );
};

export default WebcamCapture;
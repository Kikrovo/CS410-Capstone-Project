#include <Arduino.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <math.h>
#include <stdlib.h>

#define RESIZE_DIM 96  // dimensions of resized motion bitmap
#define RESIZE_DIM_SQ (RESIZE_DIM * RESIZE_DIM) // pixels in bitmap
#define RGB888_BYTES 3                 // RGB888
#define GRAYSCALE_BYTES 1              // GRAYSCALE

// motion recording parameters
int detectMotionFrames = 5; // min sequence of changed frames to confirm motion 
// define region of interest, ie exclude top and bottom of image from movement detection if required
// divide image into detectNumBands horizontal bands, define start and end bands of interest, 1 = top
int detectNumBands = 10;
int detectStartBand = 3;
int detectEndBand = 8; // inclusive
int detectChangeThreshold = 15; // min difference in pixel comparison to indicate a change
uint8_t colorDepth; // set by depthColor config
static size_t stride;
float motionVal = 8.0; // initial motion sensitivity setting

static uint8_t* currBuff = NULL;
static uint8_t* prevBuff = NULL;

//  copy by 70-95
static void rescaleImage(const uint8_t* input, int inputWidth, int inputHeight, 
                        uint8_t* output, int outputWidth, int outputHeight) {
    // use bilinear interpolation to resize image
    float xRatio = (float)inputWidth / (float)outputWidth;
    float yRatio = (float)inputHeight / (float)outputHeight;

    for (int i = 0; i < outputHeight; ++i) {
        for (int j = 0; j < outputWidth; ++j) {
            int xL = (int)floor(xRatio * j);
            int yL = (int)floor(yRatio * i);
            int xH = (int)ceil(xRatio * j);
            int yH = (int)ceil(yRatio * i);
            float xWeight = xRatio * j - xL;
            float yWeight = yRatio * i - yL;
            for (int channel = 0; channel < colorDepth; ++channel) {
                uint8_t a = input[(yL * inputWidth + xL) * colorDepth + channel];
                uint8_t b = input[(yL * inputWidth + xH) * colorDepth + channel];
                uint8_t c = input[(yH * inputWidth + xL) * colorDepth + channel];
                uint8_t d = input[(yH * inputWidth + xH) * colorDepth + channel];

                float pixel = a * (1 - xWeight) * (1 - yWeight) + b * xWeight * (1 - yWeight)
                            + c * yWeight * (1 - xWeight) + d * xWeight * yWeight;
                output[(i * outputWidth + j) * colorDepth + channel] = (uint8_t)pixel;
            }
        }
    }
}

/**
 * Convert the RGB image to a grayscale image.
 * copy by 97-104
 */
static void rgbToGray(uint8_t* buffer, int width, int height) {
    // convert rgb buffer to grayscale in place
    for (int i = 0; i < width * height; ++i) {
        int index = i * 3;
        // Calculate grayscale value using luminance formula
        buffer[i] = (uint8_t)(((77 * buffer[index]) + (150 * buffer[index + 1]) + (29 * buffer[index + 2])) >> 8);
    }
}

// =================== Core motion detection function ===================

/**
 * Core motion detection function
 * changed by 108-230
 */
bool checkMotion(uint8_t* rgbData, int width, int height, bool motionStatus) {
    // check difference between current and previous image (subtract background)
    static uint32_t motionCnt = 0;  // The number of consecutive frames in which motion was detected.
    
    // ========== Memory allocation and initialization ==========
    // changed by 118-135
    if (currBuff == NULL) {
        currBuff = (uint8_t*)malloc(RESIZE_DIM_SQ * colorDepth); 
        if (currBuff == NULL) {
            Serial.println("Error: Failed to allocate currBuff");
            return motionStatus;
        }
    }
    
    if (prevBuff == NULL) {
        prevBuff = (uint8_t*)malloc(RESIZE_DIM_SQ * colorDepth);
        if (prevBuff == NULL) {
            Serial.println("Error: Failed to allocate prevBuff");
            free(currBuff);
            currBuff = NULL;
            return motionStatus;
        }
        memset(prevBuff, 0, RESIZE_DIM_SQ * colorDepth);
    }
    

    // Create a temporary buffer.(118)
    uint8_t* rgbBuf = (uint8_t*)malloc(width * height * colorDepth);
    if (rgbBuf == NULL) {
        Serial.println("Error: Failed to allocate rgbBuf");
        return motionStatus;
    }
    
    // copy image 
    memcpy(rgbBuf, rgbData, width * height * colorDepth);
    
    // changed by 140-144
    if (colorDepth == GRAYSCALE_BYTES) {
        rgbToGray(rgbBuf, width, height);
    }
    
    // changed by(146)
    rescaleImage(rgbBuf, width, height, currBuff, RESIZE_DIM, RESIZE_DIM);
    
    free(rgbBuf);
    rgbBuf = NULL;
    
    // ========== Pixel comparison and motion detection ==========
    // copy by 158-185
    int changeCount = 0;
    // set horizontal region of interest in image 
    uint16_t startPixel = (RESIZE_DIM*(detectStartBand-1)/detectNumBands) * RESIZE_DIM * colorDepth;
    uint16_t endPixel = (RESIZE_DIM*(detectEndBand)/detectNumBands) * RESIZE_DIM * colorDepth;
    int moveThreshold = ((endPixel-startPixel)/colorDepth) * (11-motionVal)/100; // number of changed pixels that constitute a movement
    
    for (int i = 0; i < RESIZE_DIM_SQ * colorDepth; i += colorDepth) {
        uint16_t currPix = 0, prevPix = 0;
        for (int j = 0; j < colorDepth; j++) {
            currPix += currBuff[i + j];
            prevPix += prevBuff[i + j];
        }
        currPix /= colorDepth;
        prevPix /= colorDepth;
        
        // determine pixel change status
        if (abs((int)currPix - (int)prevPix) > detectChangeThreshold) {
            if (i > startPixel && i < endPixel) changeCount++; // number of changed pixels
        }
    }
    
    // ========== Save the current frame for comparison later. ==========
    // copy by 187
    memcpy(prevBuff, currBuff, RESIZE_DIM_SQ * colorDepth); // save image for next comparison 
    
    // ========== Motion state determination ==========
    // changed by 198-221
    if (changeCount > moveThreshold) {
        motionCnt++; // number of consecutive changes
        // need minimum sequence of changes to signal valid movement
        if (!motionStatus && motionCnt >= detectMotionFrames) {
            motionStatus = true; // motion started
            Serial.print("Motion START - Changed pixels: ");
            Serial.print(changeCount);
            Serial.print("/");
            Serial.println(moveThreshold);
        } 
    } else motionCnt = 0;
    
    if (motionStatus && motionCnt == 0) {
        // insufficient change or motion not classified
        Serial.println("Motion STOP");
        motionStatus = false; // motion stopped
    }
    
    if (motionStatus) {
        Serial.print("Motion ongoing - frames: ");
        Serial.println(motionCnt);
    }
    
    return motionStatus;
}


/**
 * Initialize motion detection.
 */
void setupMotionDetection(bool useColor) {
    colorDepth = useColor ? RGB888_BYTES : GRAYSCALE_BYTES;
    stride = (colorDepth == RGB888_BYTES) ? GRAYSCALE_BYTES : RGB888_BYTES;
    
    Serial.print("Motion detection setup: ");
    Serial.println(useColor ? "Color mode" : "Grayscale mode");
    
    detectMotionFrames = 5;
    detectChangeThreshold = 15;
    motionVal = 8.0;
    detectNumBands = 10;
    detectStartBand = 3;
    detectEndBand = 8;
}

/**
 * Set motion detection parameters
 */
void setMotionParams(int frames, int threshold, float sensitivity) {
    detectMotionFrames = frames;
    detectChangeThreshold = threshold;
    motionVal = sensitivity;
    
    Serial.print("Motion params updated: frames=");
    Serial.print(frames);
    Serial.print(", threshold=");
    Serial.print(threshold);
    Serial.print(", sensitivity=");
    Serial.println(sensitivity);
}

/**
 *Set the detection area.
 */
void setDetectionRegion(int numBands, int startBand, int endBand) {
    detectNumBands = numBands;
    detectStartBand = startBand;
    detectEndBand = endBand;
    
    Serial.print("Detection region: bands=");
    Serial.print(numBands);
    Serial.print(", start=");
    Serial.print(startBand);
    Serial.print(", end=");
    Serial.println(endBand);
}

/**
 * Clean up memory resources
 */
void cleanupMotionDetection() {
    if (currBuff != NULL) {
        free(currBuff);
        currBuff = NULL;
        Serial.println("currBuff freed");
    }
    
    if (prevBuff != NULL) {
        free(prevBuff);
        prevBuff = NULL;
        Serial.println("prevBuff freed");
    }
}


void setup() {
}
void loop() {
}

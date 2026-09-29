/**
 * @file  door_detector.h
 * @brief Standalone Door Open/Close Detector and Counter for TI mmWave Radar (AWR1843)
 *
 * This module runs directly on the AWR1843 Cortex-R4F MCU (MSS).
 * It evaluates 3D point cloud and range reflection data inside a configurable
 * Door Region of Interest (ROI), applies a debounced finite state machine (FSM),
 * maintains door open/close counts, and drives hardware indicators (LED / GPIO / UART).
 */

#ifndef DOOR_DETECTOR_H_
#define DOOR_DETECTOR_H_

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>

/**
 * @brief Door operational states
 */
typedef enum {
    DOOR_STATE_UNKNOWN = 0,
    DOOR_STATE_CLOSED  = 1,
    DOOR_STATE_OPENING = 2,
    DOOR_STATE_OPEN    = 3,
    DOOR_STATE_CLOSING = 4
} DoorState_e;

/**
 * @brief Configuration parameters for door detection
 */
typedef struct {
    float rangeMin;              /**< Min range boundary of door zone in meters (e.g. 0.4 m) */
    float rangeMax;              /**< Max range boundary of door zone in meters (e.g. 1.8 m) */
    float xMin;                  /**< Min lateral X boundary in meters (e.g. -0.8 m) */
    float xMax;                  /**< Max lateral X boundary in meters (e.g. +0.8 m) */
    float zMin;                  /**< Min elevation Z boundary in meters (e.g. -1.0 m) */
    float zMax;                  /**< Max elevation Z boundary in meters (e.g. +1.0 m) */
    uint16_t minPoints;          /**< Min points required to confirm door presence (e.g. 2) */
    float minSnr;                /**< Min SNR threshold for reflection */
    uint16_t debounceOpenFrames; /**< Consecutive frames required to declare OPEN (e.g. 5 = 500ms) */
    uint16_t debounceCloseFrames;/**< Consecutive frames required to declare CLOSED (e.g. 5 = 500ms) */
    uint8_t autoCalibrate;       /**< 1: Automatically calibrate closed door distance on boot */
    uint16_t calibFrameCount;    /**< Number of frames for auto-calibration (e.g. 30 = 3s) */
} DoorDetector_Config_t;

#define DOOR_EVENT_HISTORY_SIZE 4

/**
 * @brief Transition event log record
 */
typedef struct {
    DoorState_e prevState;
    DoorState_e newState;
    uint32_t frameNum;
    uint32_t openCount;
    uint32_t closeCount;
    float distance;
    float snr;
} DoorEventRecord_t;

/**
 * @brief Live telemetry and statistics
 */
typedef struct {
    DoorState_e currentState;    /**< Current debounced door state */
    DoorState_e candidateState;  /**< Raw instant frame state candidate */
    uint32_t totalOpenCount;     /**< Cumulative times the door opened */
    uint32_t totalCloseCount;    /**< Cumulative times the door closed */
    uint32_t frameCount;         /**< Total processed frames */
    uint16_t openDebounceCounter;/**< Running open debounce accumulator */
    uint16_t closeDebounceCounter;/**< Running close debounce accumulator */
    uint16_t pointsInDoorZone;   /**< Detected radar points in door ROI this frame */
    float avgDoorDistance;       /**< Average distance of door points in meters */
    float peakSnr;               /**< Maximum SNR inside door zone */
    uint32_t openDurationMs;     /**< Milliseconds spent in current OPEN state */
    uint32_t stateDurationMs;    /**< Total milliseconds spent in current state */
    uint8_t isCalibrated;        /**< 1 if auto-calibration is complete */
    uint8_t stateChangedFlag;    /**< 1 if state transitioned on the current frame */
    uint8_t vt100Mode;           /**< 1: VT100 full-screen dashboard, 0: raw line log */
    DoorEventRecord_t history[DOOR_EVENT_HISTORY_SIZE]; /**< Recent event records */
    uint8_t historyCount;        /**< Count of valid history entries */
} DoorDetector_Status_t;

/**
 * @brief Point representation compatible with DPIF_PointCloudCartesian
 */
typedef struct {
    float x;        /**< X coordinate in meters */
    float y;        /**< Y coordinate (depth/range) in meters */
    float z;        /**< Z coordinate in meters */
    float velocity; /**< Doppler velocity in m/s */
} DoorPoint_t;

/**
 * @brief Point side information compatible with DPIF_PointCloudSideInfo
 */
typedef struct {
    int16_t snr;    /**< CFAR cell-to-side noise ratio in steps of 0.1 dB */
    int16_t noise;  /**< CFAR noise in steps of 0.1 dB */
} DoorPointSideInfo_t;

/* API Functions */
void DoorDetector_init(const DoorDetector_Config_t *cfg);
void DoorDetector_processFrame(
    const DoorPoint_t *points,
    const DoorPointSideInfo_t *sideInfo,
    uint32_t numPoints,
    uint32_t framePeriodMs
);
const DoorDetector_Status_t* DoorDetector_getStatus(void);
void DoorDetector_resetCounters(void);
void DoorDetector_triggerCalibration(void);
const char* DoorDetector_stateToString(DoorState_e state);
void DoorDetector_setVt100Mode(uint8_t enable);
uint8_t DoorDetector_getVt100Mode(void);
uint32_t DoorDetector_formatVt100Screen(char *outBuf, uint32_t maxLen);

#ifdef __cplusplus
}
#endif

#endif /* DOOR_DETECTOR_H_ */

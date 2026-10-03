/**
 * @file  door_detector.h
 * @brief Standalone Door Open/Close Detector and Event Counter for TI mmWave Radar (AWR1843)
 * @version 1.3.0
 *
 * This module runs directly on the AWR1843 Cortex-R4F MCU (MSS).
 * It evaluates 3D point cloud and range reflection data inside a configurable
 * Door Region of Interest (ROI), applies a debounced finite state machine (FSM),
 * maintains door open/close counts, and drives hardware indicators (LED / GPIO / UART).
 *
 * Designed for production deployments in standalone, battery, or edge-connected IoT installations.
 */

#ifndef DOOR_DETECTOR_H_
#define DOOR_DETECTOR_H_

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/* Module Versioning */
#define DOOR_DETECTOR_VERSION_MAJOR 1
#define DOOR_DETECTOR_VERSION_MINOR 3
#define DOOR_DETECTOR_VERSION_PATCH 0

/* Maximum History Records Buffer Size */
#define DOOR_EVENT_HISTORY_SIZE 4

/* Physical Parameter Boundary Constraints for Validation */
#define DOOR_RANGE_MIN_LIMIT        0.10f   /**< 10 cm absolute sensor minimum */
#define DOOR_RANGE_MAX_LIMIT        5.00f   /**< 5.0 m absolute sensor maximum */
#define DOOR_LATERAL_MAX_LIMIT      3.00f   /**< +/- 3.0 m lateral X limit */
#define DOOR_ELEVATION_MAX_LIMIT    3.00f   /**< +/- 3.0 m elevation Z limit */
#define DOOR_MIN_DEBOUNCE_FRAMES    1U      /**< Minimum debounce frame count */
#define DOOR_MAX_DEBOUNCE_FRAMES    100U    /**< Maximum debounce frame count (10s) */

/**
 * @brief Return codes for Door Detector API functions
 */
typedef enum {
    DOOR_OK                  =  0,  /**< Operation successful */
    DOOR_ERR_INVALID_PARAM   = -1,  /**< Invalid parameter or out of physical bounds */
    DOOR_ERR_NULL_POINTER    = -2,  /**< NULL pointer passed to required argument */
    DOOR_ERR_BUFFER_OVERFLOW = -3,  /**< Provided buffer too small for output data */
    DOOR_ERR_NOT_CALIBRATED  = -4   /**< Operation requires calibrated baseline */
} DoorResult_e;

/**
 * @brief Door operational states
 */
typedef enum {
    DOOR_STATE_UNKNOWN = 0,         /**< Initializing or indeterminate */
    DOOR_STATE_CLOSED  = 1,         /**< Door presence detected inside ROI */
    DOOR_STATE_OPENING = 2,         /**< Transitional opening in progress */
    DOOR_STATE_OPEN    = 3,         /**< Door absent / passage open */
    DOOR_STATE_CLOSING = 4          /**< Transitional closing in progress */
} DoorState_e;

/**
 * @brief System Health and Operational Status
 */
typedef enum {
    DOOR_HEALTH_OK        = 0,      /**< Radar data path and MCU operating normally */
    DOOR_HEALTH_DEGRADED  = 1,      /**< High clutter or marginal reflection SNR */
    DOOR_HEALTH_FAULT     = 2       /**< Radar frame drop or abnormal data path */
} DoorHealth_e;

/**
 * @brief Configuration parameters for door detection
 */
typedef struct {
    float rangeMin;                 /**< Min range boundary of door zone in meters (e.g. 0.4 m) */
    float rangeMax;                 /**< Max range boundary of door zone in meters (e.g. 1.8 m) */
    float xMin;                     /**< Min lateral X boundary in meters (e.g. -0.8 m) */
    float xMax;                     /**< Max lateral X boundary in meters (e.g. +0.8 m) */
    float zMin;                     /**< Min elevation Z boundary in meters (e.g. -1.0 m) */
    float zMax;                     /**< Max elevation Z boundary in meters (e.g. +1.0 m) */
    uint16_t minPoints;             /**< Min points required to confirm door presence (e.g. 1) */
    float minSnr;                   /**< Min SNR threshold for valid reflection in dB (e.g. 10.0 dB) */
    uint16_t debounceOpenFrames;    /**< Consecutive frames required to declare OPEN (e.g. 5 = 500ms) */
    uint16_t debounceCloseFrames;   /**< Consecutive frames required to declare CLOSED (e.g. 5 = 500ms) */
    uint8_t autoCalibrate;          /**< 1: Automatically calibrate closed door distance on boot */
    uint16_t calibFrameCount;       /**< Number of frames for auto-calibration (e.g. 20 = 2s) */
} DoorDetector_Config_t;

/**
 * @brief Transition event log record
 */
typedef struct {
    DoorState_e prevState;          /**< State preceding the transition */
    DoorState_e newState;           /**< New confirmed state */
    uint32_t frameNum;              /**< Frame number when transition occurred */
    uint32_t openCount;             /**< Cumulative open count at transition */
    uint32_t closeCount;            /**< Cumulative close count at transition */
    float distance;                 /**< Mean distance at transition in meters */
    float snr;                      /**< Peak reflection SNR at transition in dB */
} DoorEventRecord_t;

/**
 * @brief Live telemetry and statistics structure
 */
typedef struct {
    DoorState_e currentState;       /**< Current debounced door state */
    DoorState_e candidateState;     /**< Raw instant frame state candidate */
    uint32_t totalOpenCount;        /**< Cumulative times the door opened */
    uint32_t totalCloseCount;       /**< Cumulative times the door closed */
    uint32_t frameCount;            /**< Total processed frames */
    uint16_t openDebounceCounter;   /**< Running open debounce accumulator */
    uint16_t closeDebounceCounter;  /**< Running close debounce accumulator */
    uint16_t pointsInDoorZone;      /**< Detected radar points in door ROI this frame */
    float avgDoorDistance;          /**< Average distance of door points in meters */
    float peakSnr;                  /**< Maximum SNR inside door zone in dB */
    uint32_t openDurationMs;        /**< Milliseconds spent in current OPEN state */
    uint32_t stateDurationMs;       /**< Total milliseconds spent in current state */
    uint8_t isCalibrated;           /**< 1 if auto-calibration is complete */
    uint8_t stateChangedFlag;       /**< 1 if state transitioned on the current frame */
    uint8_t vt100Mode;              /**< 1: VT100 full-screen dashboard, 0: raw line log */
    DoorEventRecord_t history[DOOR_EVENT_HISTORY_SIZE]; /**< Circular event records */
    uint8_t historyCount;           /**< Count of valid history entries */
} DoorDetector_Status_t;

/**
 * @brief Production Health & Diagnostic Telemetry
 */
typedef struct {
    uint32_t totalFramesProcessed;  /**< Total frames received from radar data path */
    uint32_t totalPointsAnalyzed;   /**< Cumulative 3D points evaluated */
    uint32_t maxPointsInFrame;      /**< Maximum points observed in a single frame */
    float maxObservedSnr;           /**< Maximum SNR observed since boot in dB */
    uint32_t uptimeSeconds;         /**< Total running uptime in seconds */
    DoorHealth_e healthStatus;      /**< Sensor operational health grade */
    uint32_t droppedFrameAlerts;    /**< Count of detected frame timing anomalies */
} DoorDiagnostics_t;

/**
 * @brief Point representation compatible with DPIF_PointCloudCartesian
 */
typedef struct {
    float x;                        /**< X coordinate in meters (lateral) */
    float y;                        /**< Y coordinate in meters (depth/boresight) */
    float z;                        /**< Z coordinate in meters (elevation) */
    float velocity;                 /**< Doppler velocity in m/s */
} DoorPoint_t;

/**
 * @brief Point side information compatible with DPIF_PointCloudSideInfo
 */
typedef struct {
    int16_t snr;                    /**< CFAR cell-to-side noise ratio in steps of 0.1 dB */
    int16_t noise;                  /**< CFAR noise in steps of 0.1 dB */
} DoorPointSideInfo_t;

/* =========================================================================
 * Public API Functions
 * ========================================================================= */

/**
 * @brief Initializes the door detector module with specified or default configuration
 * @param[in] cfg Pointer to configuration structure, or NULL to load factory defaults
 * @return DOOR_OK on success, or error code on invalid parameters
 */
DoorResult_e DoorDetector_init(const DoorDetector_Config_t *cfg);

/**
 * @brief Validates a configuration structure against physical radar limits
 * @param[in] cfg Configuration structure to validate
 * @return DOOR_OK if valid, DOOR_ERR_INVALID_PARAM or DOOR_ERR_NULL_POINTER otherwise
 */
DoorResult_e DoorDetector_validateConfig(const DoorDetector_Config_t *cfg);

/**
 * @brief Updates operational configuration dynamically at runtime
 * @param[in] cfg New configuration parameters to apply
 * @return DOOR_OK on success, or error code on validation failure
 */
DoorResult_e DoorDetector_setConfig(const DoorDetector_Config_t *cfg);

/**
 * @brief Retrieves the active configuration parameters
 * @param[out] cfg Pointer to store copy of active configuration
 * @return DOOR_OK on success, DOOR_ERR_NULL_POINTER on NULL argument
 */
DoorResult_e DoorDetector_getConfig(DoorDetector_Config_t *cfg);

/**
 * @brief Core frame processing pipeline - evaluates point cloud and updates FSM
 * @param[in] points Array of 3D Cartesian points from range/angle processing
 * @param[in] sideInfo Array of CFAR SNR/Noise metrics corresponding to points (optional, may be NULL)
 * @param[in] numPoints Number of points in the arrays
 * @param[in] framePeriodMs Nominal frame period in milliseconds (e.g. 100 ms)
 */
void DoorDetector_processFrame(
    const DoorPoint_t *points,
    const DoorPointSideInfo_t *sideInfo,
    uint32_t numPoints,
    uint32_t framePeriodMs
);

/**
 * @brief Retrieves direct read-only pointer to internal live status structure
 * @return Const pointer to current detector status
 */
const DoorDetector_Status_t* DoorDetector_getStatus(void);

/**
 * @brief Performs an atomic, thread-safe snapshot copy of the status structure
 * @param[out] outSnapshot Destination buffer to copy status into
 * @return DOOR_OK on success, DOOR_ERR_NULL_POINTER on NULL argument
 */
DoorResult_e DoorDetector_getSnapshot(DoorDetector_Status_t *outSnapshot);

/**
 * @brief Retrieves production diagnostic and health metrics
 * @param[out] diag Destination buffer to copy diagnostics into
 * @return DOOR_OK on success, DOOR_ERR_NULL_POINTER on NULL argument
 */
DoorResult_e DoorDetector_getDiagnostics(DoorDiagnostics_t *diag);

/**
 * @brief Resets cumulative open and close cycle counters back to zero
 */
void DoorDetector_resetCounters(void);

/**
 * @brief Triggers an automatic closed-door distance recalibration cycle
 */
void DoorDetector_triggerCalibration(void);

/**
 * @brief Converts door operational state enum to human-readable string
 * @param[in] state Operational state enum
 * @return Constant string representation ("CLOSED", "OPEN", etc.)
 */
const char* DoorDetector_stateToString(DoorState_e state);

/**
 * @brief Enables or disables on-chip VT100 console rendering over UART
 * @param[in] enable 1 to enable VT100 dashboard, 0 for single-line log
 */
void DoorDetector_setVt100Mode(uint8_t enable);

/**
 * @brief Queries current VT100 console mode setting
 * @return 1 if VT100 mode enabled, 0 if disabled
 */
uint8_t DoorDetector_getVt100Mode(void);

/**
 * @brief Formats the complete VT100 live dashboard into provided string buffer
 * @param[out] outBuf Destination text buffer
 * @param[in] maxLen Maximum buffer capacity in bytes
 * @return Number of characters written to buffer
 */
uint32_t DoorDetector_formatVt100Screen(char *outBuf, uint32_t maxLen);

#ifdef __cplusplus
}
#endif

#endif /* DOOR_DETECTOR_H_ */

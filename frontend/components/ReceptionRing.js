import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import useChimeSound from '../hooks/useChimeSound';

/**
 * Premium Reception Ring notification modal.
 * Displays incoming visitor calls with animated entrance.
 */
export function ReceptionRing({ ring, onDismiss, onResponse }) {
  const [isVisible, setIsVisible] = useState(false);
  const { startLoop, stopLoop, playChime } = useChimeSound();
  
  // Handle ring data changes
  useEffect(() => {
    if (ring) {
      setIsVisible(true);
      // Initialize audio on first interaction and start loop
      playChime();
      startLoop(2500);
    }
    
    return () => {
      stopLoop();
    };
  }, [ring, playChime, startLoop, stopLoop]);
  
  const handleDismiss = useCallback(() => {
    stopLoop();
    setIsVisible(false);
    setTimeout(() => {
      onDismiss?.();
    }, 300);
  }, [stopLoop, onDismiss]);
  
  const handleResponse = useCallback(async (response) => {
    stopLoop();
    setIsVisible(false);
    
    setTimeout(() => {
      onResponse?.(response);
    }, 300);
  }, [stopLoop, onResponse]);
  
  // Animation variants
  const slideDownVariant = {
    hidden: {
      y: '-100%',
      opacity: 0,
    },
    visible: {
      y: 0,
      opacity: 1,
      transition: {
        type: 'spring',
        stiffness: 300,
        damping: 25,
      },
    },
    exit: {
      y: '-100%',
      opacity: 0,
      transition: {
        duration: 0.2,
      },
    },
  };
  
  const contentVariant = {
    hidden: { scale: 0.9, opacity: 0 },
    visible: {
      scale: 1,
      opacity: 1,
      transition: {
        delay: 0.1,
        duration: 0.3,
      },
    },
  };
  
  const buttonVariant = {
    hidden: { y: 20, opacity: 0 },
    visible: (i) => ({
      y: 0,
      opacity: 1,
      transition: {
        delay: 0.2 + i * 0.1,
        duration: 0.3,
      },
    }),
  };
  
  if (!ring) return null;
  
  return (
    <AnimatePresence>
      {isVisible && (
        <div style={styles.overlay}>
          <motion.div
            style={styles.modalContainer}
            variants={slideDownVariant}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            {/* Decorative top bar */}
            <motion.div
              style={styles.topBar}
              initial={{ scaleX: 0 }}
              animate={{ scaleX: 1 }}
              transition={{ delay: 0.15, duration: 0.4 }}
            />
            
            {/* Content */}
            <motion.div style={styles.content} variants={contentVariant}>
              {/* Caller icon */}
              <div style={styles.iconContainer}>
                <svg
                  width="48"
                  height="48"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
              </div>
              
              {/* Header */}
              <div style={styles.header}>
                <span style={styles.label}>Incoming Call</span>
                <h2 style={styles.callerName}>{ring.callerName}</h2>
              </div>
              
              {/* Message */}
              <p style={styles.message}>{ring.message}</p>
              
              {/* Ring indicator */}
              <div style={styles.ringIndicator}>
                <span style={styles.ringDot} />
                <span style={styles.ringText}>LIVE</span>
              </div>
            </motion.div>
            
            {/* Action buttons */}
            <div style={styles.buttonContainer}>
              <motion.button
                style={{ ...styles.button, ...styles.comingButton }}
                onClick={() => handleResponse('coming')}
                variants={buttonVariant}
                initial="hidden"
                animate="visible"
                custom={0}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                I'm Coming
              </motion.button>
              
              <motion.button
                style={{ ...styles.button, ...styles.busyButton }}
                onClick={() => handleResponse('busy')}
                variants={buttonVariant}
                initial="hidden"
                animate="visible"
                custom={1}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
                Busy
              </motion.button>
            </motion.div>
            
            {/* Dismiss hint */}
            <motion.p
              style={styles.dismissHint}
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.6 }}
              transition={{ delay: 0.5 }}
            >
              Tap anywhere to dismiss
            </motion.p>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

// Premium minimalist styles
const styles = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    zIndex: 9999,
    display: 'flex',
    justifyContent: 'center',
    padding: '20px',
    background: 'transparent',
  },
  modalContainer: {
    width: '100%',
    maxWidth: '400px',
    background: 'rgba(255, 255, 255, 0.98)',
    borderRadius: '24px',
    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(0, 0, 0, 0.05)',
    overflow: 'hidden',
    backdropFilter: 'blur(20px)',
  },
  topBar: {
    height: '4px',
    background: 'linear-gradient(90deg, #667eea 0%, #764ba2 100%)',
    transformOrigin: 'left',
  },
  content: {
    padding: '32px 24px 16px',
    textAlign: 'center',
  },
  iconContainer: {
    width: '80px',
    height: '80px',
    margin: '0 auto 20px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    borderRadius: '50%',
    color: 'white',
    boxShadow: '0 10px 40px rgba(102, 126, 234, 0.4)',
  },
  header: {
    marginBottom: '8px',
  },
  label: {
    display: 'inline-block',
    fontSize: '11px',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: '1.5px',
    color: '#667eea',
    marginBottom: '8px',
  },
  callerName: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    fontSize: '28px',
    fontWeight: '700',
    color: '#1a1a2e',
    margin: 0,
    lineHeight: 1.2,
  },
  message: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    fontSize: '15px',
    color: '#64748b',
    margin: '8px 0 0',
    lineHeight: 1.5,
  },
  ringIndicator: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    marginTop: '16px',
  },
  ringDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    background: '#ef4444',
    boxShadow: '0 0 0 4px rgba(239, 68, 68, 0.2)',
    animation: 'pulse 1.5s ease-in-out infinite',
  },
  ringText: {
    fontSize: '10px',
    fontWeight: '600',
    letterSpacing: '1.5px',
    color: '#ef4444',
  },
  buttonContainer: {
    display: 'flex',
    gap: '12px',
    padding: '0 24px 24px',
  },
  button: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    padding: '16px 24px',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    fontSize: '15px',
    fontWeight: '600',
    border: 'none',
    borderRadius: '16px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  comingButton: {
    background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
    color: 'white',
    boxShadow: '0 4px 15px rgba(16, 185, 129, 0.3)',
  },
  busyButton: {
    background: '#f1f5f9',
    color: '#64748b',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)',
  },
  dismissHint: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    fontSize: '12px',
    textAlign: 'center',
    color: '#94a3b8',
    paddingBottom: '16px',
  },
};

// Add keyframe animation via style tag
if (typeof document !== 'undefined') {
  const styleSheet = document.createElement('style');
  styleSheet.textContent = `
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }
  `;
  document.head.appendChild(styleSheet);
}

export default ReceptionRing;
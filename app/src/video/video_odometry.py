import numpy as np
import cv2


class MonoVideoOdometery(object):
    def __init__(self,
                 focal_length=1188,
                 pp=(960.0, 540.0),
                 lk_params=dict(winSize=(21, 21), criteria=(
                     cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01)),
                 detector=cv2.FastFeatureDetector.create(threshold=25, nonmaxSuppression=True)):

        self.detector = detector
        self.lk_params = lk_params
        self.focal = focal_length
        self.pp = pp
        self.R = np.zeros(shape=(3, 3))
        self.t = np.zeros(shape=(3, 1))
        self.id = 0
        self.n_features = 0

        # Initialize feature points
        self.p0 = None
        self.good_old = None
        self.good_new = None

    def detect(self, img):
        """Detect features in image."""
        p0 = self.detector.detect(img)
        points = np.array([x.pt for x in p0],
                          dtype=np.float32).reshape(-1, 1, 2)
        return points

    def visual_odometery(self):
        """Perform visual odometry calculations."""
        # Only detect new features if we don't have enough
        if self.n_features < 2000:
            self.p0 = self.detect(self.current_frame)
        else:
            # Use the good features from last frame as starting points
            self.p0 = self.good_new.reshape(-1, 1, 2)

        # Calculate optical flow
        self.p1, st, err = cv2.calcOpticalFlowPyrLK(
            self.old_frame, self.current_frame, self.p0, None, **self.lk_params)

        # Only keep good points
        if st is not None:
            self.good_old = self.p0[st == 1]
            self.good_new = self.p1[st == 1]

            if len(self.good_new) < 8 or len(self.good_old) < 8:
                print("Not enough good matches for Essential Matrix calculation")
                return

            # Find Essential Matrix
            E, mask = cv2.findEssentialMat(
                self.good_new, self.good_old, self.focal, self.pp, cv2.RANSAC, 0.999, 1.0, None)

            if E is None:
                print("Failed to compute Essential Matrix")
                return

            # Recover pose
            _, R, t, mask = cv2.recoverPose(
                E, self.good_old, self.good_new, focal=self.focal, pp=self.pp, mask=None)

            if self.id < 2:
                self.R = R
                self.t = t
            else:
                self.t = self.t + np.linalg.norm(t)*self.R.dot(t)
                self.R = R.dot(self.R)

            self.n_features = self.good_new.shape[0]

    async def get_mono_coordinates(self):
        """Get current position in ROV frame."""
        transform = np.array([[0, 0, 1],   # Camera z -> ROV x (forward)
                              [1, 0, 0],    # Camera -x -> ROV y (left)
                              [0, -1, 0]])   # Camera -y -> ROV z (down)

        adj_coord = transform @ self.t
        return adj_coord.flatten()

    async def process_frame(self, frame):
        """Process a new frame."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if self.id == 0:
            self.current_frame = gray
            # Detect initial features
            self.p0 = self.detect(self.current_frame)
        else:
            self.old_frame = self.current_frame.copy()
            self.current_frame = gray
            self.visual_odometery()

        self.id += 1

    def get_tracking_visualization(self, frame):
        """Create debug visualization of feature tracking."""
        vis_frame = frame.copy()

        # Draw current features
        if self.good_new is not None and self.good_old is not None:
            # Draw the tracks
            for i, (new, old) in enumerate(zip(self.good_new, self.good_old)):
                a, b = new.ravel()
                c, d = old.ravel()

                # Draw line between old and new position
                cv2.line(vis_frame, (int(c), int(d)),
                         (int(a), int(b)), (0, 255, 0), 2)
                # Draw current position
                cv2.circle(vis_frame, (int(a), int(b)), 3, (0, 0, 255), -1)

        # Add debug info
        cv2.putText(vis_frame, f'Features: {self.n_features}', (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        return vis_frame

import asyncio
import numpy as np
import cv2
import os


class MonoVideoOdometery(object):
    def __init__(self,
                 video_file_path,
                 focal_length=1188.0,
                 pp=(960, 540),
                 lk_params=dict(winSize=(21, 21), criteria=(
                     cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01)),
                 detector=cv2.FastFeatureDetector.create(threshold=25, nonmaxSuppression=True)):
        '''
        Arguments:
            video_file_path {str} -- File path that leads to video file

        Keyword Arguments:
            focal_length {float} -- Focal length of camera used in video sequence (default: {718.8560})
            pp {tuple} -- Principal point of camera in video sequence (default: {(607.1928, 185.2157)})
            lk_params {dict} -- Parameters for Lucas Kanade optical flow (default: {dict(winSize  = (21,21), criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))})
            detector {cv2.FeatureDetector} -- Most types of OpenCV feature detectors (default: {cv2.FastFeatureDetector_create(threshold=25, nonmaxSuppression=True)})

        Raises:
            ValueError -- Raised when video or pose file paths are incorrect
        '''

        self.video_path = video_file_path
        self.detector = detector
        self.lk_params = lk_params
        self.focal = focal_length
        self.pp = pp
        self.R = np.zeros(shape=(3, 3))
        self.t = np.zeros(shape=(3, 3))
        self.id = 0
        self.n_features = 0

        # Open the video file
        self.cap = cv2.VideoCapture(video_file_path)
        if not self.cap.isOpened():
            raise ValueError(
                "The video file could not be opened. Please check the file path.")

        self.process_frame()

    async def hasNextFrame(self):
        '''Used to determine whether there are remaining frames in the video

        Returns:
            bool -- Boolean value denoting whether there are still frames to process
        '''
        return self.cap.isOpened()

    async def detect(self, img):
        '''Used to detect features and parse into useable format

        Arguments:
            img {np.ndarray} -- Image for which to detect keypoints on

        Returns:
            np.array -- A sequence of points in (x, y) coordinate format
            denoting location of detected keypoint
        '''

        p0 = self.detector.detect(img)

        return np.array([x.pt for x in p0], dtype=np.float32).reshape(-1, 1, 2)

    async def visual_odometery(self):
        '''
        Used to perform visual odometery. If features fall out of frame
        such that there are less than 2000 features remaining, a new feature
        detection is triggered. 
        '''

        if self.n_features < 2000:
            self.p0 = self.detect(self.old_frame)

        # Calculate optical flow between frames, st holds status
        # of points from frame to frame
        self.p1, st, err = cv2.calcOpticalFlowPyrLK(
            self.old_frame, self.current_frame, self.p0, None, **self.lk_params)

        # Save the good points from the optical flow
        self.good_old = self.p0[st == 1]
        self.good_new = self.p1[st == 1]

        E, _ = cv2.findEssentialMat(
            self.good_new, self.good_old, self.focal, self.pp, cv2.RANSAC, 0.999, 1.0, None)
        _, R, t, _ = cv2.recoverPose(
            E, self.good_old, self.good_new, focal=self.focal, pp=self.pp, mask=None)

        if self.id < 2:
            self.R = R
            self.t = t
        else:
            absolute_scale = self.get_absolute_scale()
            if (absolute_scale > 0.1 and abs(t[2][0]) > abs(t[0][0]) and abs(t[2][0]) > abs(t[1][0])):
                self.t = self.t + absolute_scale*self.R.dot(t)
                self.R = R.dot(self.R)

        self.n_features = self.good_new.shape[0]

    async def get_mono_coordinates(self):
        diag = np.array([[-1, 0, 0],
                        [0, -1, 0],
                        [0, 0, -1]])
        adj_coord = np.matmul(diag, self.t)

        return adj_coord.flatten()

    async def get_true_coordinates(self):
        '''Returns true coordinates of vehicle

        Returns:
            np.array -- Array in format [x, y, z]
        '''
        return self.true_coord.flatten()

    async def get_absolute_scale(self):
        '''Used to provide scale estimation for multiplying translation vectors

        Returns:
            float -- Scalar value allowing for scale estimation
        '''
        pose = self.pose[self.id - 1].strip().split()
        x_prev = float(pose[3])
        y_prev = float(pose[7])
        z_prev = float(pose[11])
        pose = self.pose[self.id].strip().split()
        x = float(pose[3])
        y = float(pose[7])
        z = float(pose[11])

        true_vect = np.array([[x], [y], [z]])
        self.true_coord = true_vect
        prev_vect = np.array([[x_prev], [y_prev], [z_prev]])

        return np.linalg.norm(true_vect - prev_vect)

    async def process_frame(self):
        '''Processes frames in the video sequence one by one
        '''

        ret, frame = self.cap.read()
        if not ret:
            self.cap.release()
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if self.id < 2:
            self.old_frame = gray
            self.current_frame = gray
            self.visual_odometery()
            self.id = 2
        else:
            self.old_frame = self.current_frame
            self.current_frame = gray
            self.visual_odometery()
            self.id += 1


async def visual_odometry(vo: MonoVideoOdometery, flag: bool, traj):
    while vo.hasNextFrame():
        frame = vo.current_frame
        cv2.imshow('frame', frame)
        k = cv2.waitKey(1)
        if k == 27:  # Escape key to stop
            break

        if k == 121:  # 'y' key to toggle flow lines
            flag = not flag
            def toggle_out(flag): return "On" if flag else "Off"
            print("Flow lines turned ", toggle_out(flag))
            mask = np.zeros_like(vo.old_frame)
            mask = np.zeros_like(vo.current_frame)

        await vo.process_frame()

        print(await vo.get_mono_coordinates())

        mono_coord = await vo.get_mono_coordinates()
        true_coord = await vo.get_true_coordinates()

        print("MSE Error: ", np.linalg.norm(mono_coord - true_coord))
        print("x: {}, y: {}, z: {}".format(*[str(pt) for pt in mono_coord]))
        print("true_x: {}, true_y: {}, true_z: {}".format(
            *[str(pt) for pt in true_coord]))

        draw_x, draw_y, draw_z = [int(round(x)) for x in mono_coord]
        true_x, true_y, true_z = [int(round(x)) for x in true_coord]

        traj = cv2.circle(traj, (true_x + 400, true_z + 100),
                          1, list((0, 0, 255)), 4)
        traj = cv2.circle(traj, (draw_x + 400, draw_z + 100),
                          1, list((0, 255, 0)), 4)

        cv2.putText(traj, 'Actual Position:', (140, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(traj, 'Red', (270, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        cv2.putText(traj, 'Estimated Odometry Position:', (30, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(traj, 'Green', (270, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        cv2.imshow('trajectory', traj)

        await asyncio.sleep(0)

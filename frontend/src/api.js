import axios from 'axios';

// Đảm bảo cổng này trùng với cổng Backend Python đang chạy (thường là 8000)
const api = axios.create({
    baseURL: 'http://localhost:8000',
    headers: {
        'Content-Type': 'application/json',
    },
});

// Tự động gắn Token vào mọi yêu cầu gửi đi
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

export default api;
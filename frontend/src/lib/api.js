import axios from "axios";

const api = axios.create({
  baseURL: "/api",
});

/* ================================
   Attach JWT token to every request
================================ */

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("evua_token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});


/* ================================
   Handle auth errors
================================ */

api.interceptors.response.use(
  (response) => response,
  (error) => {

    if (error.response?.status === 401) {

      localStorage.removeItem("evua_token");
      localStorage.removeItem("evua_user");

      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }

    return Promise.reject(error);
  }
);


/* ================================
   AUTH APIs
================================ */

export const loginUser = (data) =>
  api.post("/auth/login", data);

export const registerUser = (data) =>
  api.post("/auth/register", data);


/* ================================
   MIGRATION APIs
================================ */

export const runMigration = async (file) => {

  const formData = new FormData();
  formData.append("file", file);

  const res = await api.post("/migration/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return res.data;
};


/* ================================
   BENCHMARK APIs (optional)
================================ */

export const getBenchmarks = () =>
  api.get("/benchmarks");


/* ================================
   SESSION APIs
================================ */

export const getSessions = () =>
  api.get("/sessions");

export const getSession = (id) =>
  api.get(`/sessions/${id}`);


export default api;
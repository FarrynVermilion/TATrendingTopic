import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  headers: {
    'X-Api-Key': import.meta.env.VITE_API_KEY || 'default_secret_key'
  }
});

export const getCsvHeaders = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/get-headers/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

export const processGsdmm = async (file: File, textColumn: string, numTopics: number = 15) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('text_column', textColumn);
  formData.append('num_topics', numTopics.toString());
  
  const response = await api.post('/process-gsdmm/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

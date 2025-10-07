export const getAuthToken = async (): Promise<string | null> => {
    const token = localStorage.getItem('token');
    if (!token) {
        console.error('No auth token found');
        return null;
    }
    return token;
};
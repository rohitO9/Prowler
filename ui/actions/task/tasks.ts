"use server";

import {
  apiBaseUrl,
  getApiBaseUrl,
  getAuthHeaders,
  getErrorMessage,
  parseStringify,
} from "@/lib";

export const getTask = async (taskId: string) => {
  const headers = await getAuthHeaders({ contentType: false });

  const url = new URL(`${getApiBaseUrl()}/tasks/${taskId}`);

  try {
    const response = await fetch(url.toString(), {
      headers,
    });
    const data = await response.json();
    return parseStringify(data);
  } catch (error) {
    return { error: getErrorMessage(error) };
  }
};

import { apiClient } from './client';

export interface ChainArtifact {
    value: any;
    meta: {
        source_job_id: string;
        created_at: string;
        [key: string]: any;
    };
}

export interface ChainContext {
    chain_id: string;
    task_id: string;
    state: string;
    limits: Record<string, any>;
    artifacts: Record<string, ChainArtifact>;
    error: any | null;
    needs_tick: number;
}

export const chainsApi = {
    getMissionChains: async (missionId: string): Promise<ChainContext[]> => {
        const response = await apiClient.get<ChainContext[]>(`/missions/${missionId}/chains`);
        return response.data;
    },

    getChainContext: async (chainId: string): Promise<ChainContext> => {
        const response = await apiClient.get<ChainContext>(`/chains/${chainId}/context`);
        return response.data;
    }
};

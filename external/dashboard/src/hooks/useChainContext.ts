import { useQuery } from '@tanstack/react-query';
import { chainsApi, ChainContext } from '../api/chains';

export const useMissionChains = (missionId: string | undefined) => {
    return useQuery({
        queryKey: ['missions', missionId, 'chains'],
        queryFn: () => chainsApi.getMissionChains(missionId!),
        enabled: !!missionId,
        refetchInterval: 3000, // Poll artifacts every 3s
    });
};

export const useChainContext = (chainId: string | undefined) => {
    return useQuery({
        queryKey: ['chains', chainId, 'context'],
        queryFn: () => chainsApi.getChainContext(chainId!),
        enabled: !!chainId,
        refetchInterval: 2000, // Faster polling for active chain
    });
};

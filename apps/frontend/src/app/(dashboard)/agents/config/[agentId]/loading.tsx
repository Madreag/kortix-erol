import { KortixLoader } from '@/components/ui/kortix-loader';

export default function AgentConfigLoading() {
  return (
    <div className="flex items-center justify-center h-screen">
      <KortixLoader size="large" />
    </div>
  );
}

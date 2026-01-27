import { KortixLoader } from '@/components/ui/kortix-loader';

export default function TemplateLoading() {
  return (
    <div className="min-h-screen">
      <div className="flex items-center justify-center h-screen">
        <KortixLoader size="large" />
      </div>
    </div>
  );
}

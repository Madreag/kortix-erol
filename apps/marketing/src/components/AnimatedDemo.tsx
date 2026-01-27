import { useState, useEffect } from 'react';

const demoCode = `// Ask Kortix to build a feature
const response = await kortix.agent.run({
  prompt: "Add dark mode toggle to the header",
  project: "my-app",
});

// Watch as it codes in real-time
for await (const chunk of response.stream()) {
  console.log(chunk.text);
}`;

export default function AnimatedDemo() {
  const [displayedCode, setDisplayedCode] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  
  useEffect(() => {
    let index = 0;
    setIsTyping(true);
    
    const timerId = window.setInterval(() => {
      if (index < demoCode.length) {
        setDisplayedCode(demoCode.slice(0, index + 1));
        index++;
      } else {
        window.clearInterval(timerId);
        setIsTyping(false);
      }
    }, 30);
    
    return () => {
      window.clearInterval(timerId);
    };
  }, []);
  
  return (
    <div className="max-w-3xl mx-auto">
      <div className="bg-gray-800 rounded-xl overflow-hidden shadow-2xl">
        {/* Window controls */}
        <div className="flex items-center gap-2 px-4 py-3 bg-gray-900 border-b border-gray-700">
          <div className="w-3 h-3 rounded-full bg-red-500" />
          <div className="w-3 h-3 rounded-full bg-yellow-500" />
          <div className="w-3 h-3 rounded-full bg-green-500" />
          <span className="ml-4 text-sm text-gray-500">demo.ts</span>
        </div>
        
        {/* Code content */}
        <pre className="p-6 text-sm font-mono text-gray-300 overflow-x-auto">
          <code>{displayedCode}</code>
          {isTyping && <span className="animate-pulse">▌</span>}
        </pre>
      </div>
    </div>
  );
}

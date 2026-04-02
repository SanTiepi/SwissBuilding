import { memo, useCallback, useRef, useState } from 'react';
import { useTranslation } from '@/i18n';
import { Mic, MicOff } from 'lucide-react';
import { cn } from '@/utils/formatters';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type SpeechRecognitionAny = any;

interface VoiceInputProps {
  value: string;
  onChange: (text: string) => void;
  placeholder?: string;
}

export const VoiceInput = memo(function VoiceInput({ value, onChange, placeholder }: VoiceInputProps) {
  const { t } = useTranslation();
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<SpeechRecognitionAny | null>(null);

  const supportsVoice =
    typeof window !== 'undefined' &&
    ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window);

  const startListening = useCallback(() => {
    if (!supportsVoice) return;
    const SpeechRecognitionCtor =
      (window as SpeechRecognitionAny).SpeechRecognition ||
      (window as SpeechRecognitionAny).webkitSpeechRecognition;
    const recognition = new SpeechRecognitionCtor();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'fr-CH';

    recognition.onresult = (event: SpeechRecognitionAny) => {
      const transcript = event.results?.[0]?.[0]?.transcript ?? '';
      onChange(value ? `${value} ${transcript}` : transcript);
    };

    recognition.onend = () => setIsListening(false);
    recognition.onerror = () => setIsListening(false);

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
  }, [supportsVoice, value, onChange]);

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
    setIsListening(false);
  }, []);

  return (
    <div data-testid="voice-input">
      <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
        {t('observation.notes') || 'Notes'}
      </label>
      <div className="relative">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={4}
          data-testid="notes-textarea"
          placeholder={placeholder || t('observation.notes_placeholder') || 'Add notes...'}
          className="w-full rounded-xl border border-gray-300 px-4 py-3 pr-12 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
        />
        {supportsVoice && (
          <button
            type="button"
            onClick={isListening ? stopListening : startListening}
            data-testid="voice-button"
            className={cn(
              'absolute bottom-3 right-3 rounded-full p-2 transition',
              isListening
                ? 'animate-pulse bg-red-500 text-white'
                : 'bg-gray-100 text-gray-500 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400',
            )}
          >
            {isListening ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
          </button>
        )}
      </div>
    </div>
  );
});

import json
import threading
import time

from config import DEBUG

try:
	import speech_recognition as sr
except ImportError:
	sr = None

try:
	from vosk import Model as VoskModel, KaldiRecognizer
except ImportError:
	VoskModel = None
	KaldiRecognizer = None


class VoiceListener:
	def __init__(
		self,
		wake_phrases,
		on_trigger,
		mic_name=None,
		mic_index=None,
		listen_timeout=3.0,
		phrase_time_limit=4.0,
		language="en-US",
		engine="google",
		vosk_model_path=None,
		commands=None,
		on_command=None,
	):
		self.engine = (engine or "google").lower()
		self.vosk_model_path = vosk_model_path
		self.vosk_model = None
		self.vosk_recognizer = None
		self.available = sr is not None
		self.wake_phrases = []
		for phrase in (wake_phrases or []):
			normalized = self._normalize_phrase(phrase)
			if normalized:
				self.wake_phrases.append(normalized)
		self.on_trigger = on_trigger
		self.mic_name = mic_name
		self.mic_index = mic_index
		self.listen_timeout = listen_timeout
		self.phrase_time_limit = phrase_time_limit
		self.language = language
		
		self.commands = commands or {}
		self.on_command = on_command

		self.recognizer = sr.Recognizer() if self.available else None
		if self.recognizer:
			self.recognizer.energy_threshold = 300
			self.recognizer.dynamic_energy_threshold = True

		if self.engine == "vosk":
			if VoskModel is None or KaldiRecognizer is None:
				self.available = False
			elif not self.vosk_model_path:
				print("VOSK model path is missing")
				self.available = False
			else:
				try:
					self.vosk_model = VoskModel(self.vosk_model_path)
					
					# Grammar constraints:
					# Allow only specific words to reduce false positives from TV/background noise.
					grammar = []
					
					if self.wake_phrases:
						grammar.extend(self.wake_phrases)
					
					if self.commands:
						for phrases in self.commands.values():
							grammar.extend(phrases)
					
					unique_phrases = set()
					for p in grammar:
						clean_p = p.lower().strip()
						if clean_p:
							unique_phrases.add(clean_p)
					
					# Add [unk] to handle noise and unknown words
					unique_phrases.add("[unk]") 
					grammar_json = json.dumps(list(unique_phrases))
					
					if DEBUG:
						print(f"Vosk grammar: {grammar_json}")

					self.vosk_recognizer = KaldiRecognizer(self.vosk_model, 16000, grammar_json)
					self.vosk_recognizer.SetWords(True)
				except Exception as exc:
					print(f"Vosk initialization failed: {exc}")
					self.available = False

		self.microphone = None
		self.thread = None
		self.running = False
		self.paused = False

	def start(self):
		if not self.available:
			return False
		if self.running:
			return True

		try:
			index = self._select_device_index()
			if DEBUG:
				print(f"Microphone: index={index} name={self.mic_name}")
			self.microphone = sr.Microphone(device_index=index)
		except Exception as exc:
			print(f"Microphone initialization failed: {exc}")
			return False

		self.running = True
		self.thread = threading.Thread(target=self._listen_loop, daemon=True)
		self.thread.start()
		return True

	def stop(self):
		self.running = False
		if self.thread and self.thread.is_alive():
			self.thread.join(timeout=1.0)

	def pause(self):
		self.paused = True
		if DEBUG:
			print("Voice listening paused")

	def resume(self):
		self.paused = False
		if DEBUG:
			print("Voice listening resumed")

	def is_paused(self):
		return self.paused

	def _select_device_index(self):
		if self.mic_index is not None:
			return self.mic_index

		try:
			devices = sr.Microphone.list_microphone_names()
		except Exception as exc:
			print(f"Failed to list microphones: {exc}")
			return None

		if self.mic_name:
			lowered = self.mic_name.lower()
			for idx, name in enumerate(devices):
				if lowered in name.lower():
					return idx

		return None

	def _listen_loop(self):
		assert self.microphone is not None
		with self.microphone as source:
			try:
				self.recognizer.adjust_for_ambient_noise(source, duration=1)
				if DEBUG:
					print("Noise threshold calibrated")
			except Exception as exc:
				print(f"Noise calibration failed: {exc}")

			while self.running:
				if self.paused:
					time.sleep(0.1)
					continue
				
				try:
					audio = self.recognizer.listen(
						source,
						timeout=self.listen_timeout,
						phrase_time_limit=self.phrase_time_limit,
					)
				except sr.WaitTimeoutError:
					continue
				except Exception as exc:
					if DEBUG:
						print(f"Listen error: {exc}")
					time.sleep(0.2)
					continue

				# Check paused state again after recording
				if self.paused:
					if DEBUG:
						print("Audio captured but paused; discarding")
					continue

				if DEBUG:
					sample_rate = audio.sample_rate or 0
					sample_width = audio.sample_width or 0
					frame_len = len(audio.frame_data) or 0
					sample_count = frame_len / max(sample_width, 1)
					duration = sample_count / sample_rate if sample_rate else 0.0
					print(
						f"Captured audio segment: len={frame_len} bytes | {duration:.2f}s | {sample_rate}Hz | width={sample_width}"
					)

				transcript = self._transcribe(audio)
				if DEBUG:
					if transcript:
						print(f"Recognized text: {transcript}")
					else:
						print("No speech recognized; waiting for next segment")
				if not transcript:
					continue

				# First, check if it matches a command
				matched_command = self._match_command(transcript)
				if matched_command:
					if DEBUG:
						print(f"Matched command: {matched_command}")
					if self.on_command:
						try:
							self.on_command(matched_command, transcript)
						except Exception as exc:
							print(f"Command callback failed: {exc}")
					continue

				# Then, check wake phrases
				if self._contains_wake_phrase(transcript):
					if DEBUG:
						print(f"Captured speech: {transcript}")
					try:
						self.on_trigger(transcript)
					except Exception as exc:
						print(f"Voice callback failed: {exc}")

	def _transcribe(self, audio):
		if self.engine == "vosk" and self.vosk_recognizer:
			try:
				raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
				# Regardless of what AcceptWaveform returns, we always read FinalResult
				# because sr.listen has already captured a complete speech segment.
				self.vosk_recognizer.AcceptWaveform(raw)
				result = json.loads(self.vosk_recognizer.FinalResult())
				text = result.get("text", "").strip().lower()
				
				if DEBUG:
					print(f"Vosk result: {text}")
				
				# FinalResult resets the recognizer state; ensure no stale commands are cached
				self.vosk_recognizer.Reset()
				
				return text or None
			except Exception as exc:
				print(f"Vosk recognition failed: {exc}")
				return None

		try:
			return self.recognizer.recognize_google(audio, language=self.language).lower()
		except sr.UnknownValueError:
			return None
		except sr.RequestError as exc:
			print(f"Unable to reach speech recognition service: {exc}")
			time.sleep(2)
			return None
		except Exception as exc:
			print(f"Speech recognition error: {exc}")
			return None

	def _contains_wake_phrase(self, transcript):
		if not transcript:
			return False
		normalized = self._normalize_phrase(transcript)
		return any(phrase in normalized for phrase in self.wake_phrases)

	def _match_command(self, transcript):
		if not transcript or not self.commands:
			return None
		normalized = self._normalize_phrase(transcript)
		for cmd_name, phrases in self.commands.items():
			for phrase in phrases:
				norm_phrase = self._normalize_phrase(phrase)
				if norm_phrase and norm_phrase in normalized:
					return cmd_name
		return None

	@staticmethod
	def _normalize_phrase(phrase):
		if not phrase:
			return ""
		return " ".join(
			phrase.lower()
			.replace("_", " ")
			.replace("-", " ")
			.split()
		)


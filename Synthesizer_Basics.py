# Name: Synthesizer
# Author: Bocaletto Luca
# Description: Riceve MIDI Input esempio da una tastierae e Genera Suoni corrispondenti alla nota suonata, prova a emulare un oscillatore con le 4 forme d'onda principali e integra anche un Envelope
import mido  # Importa la libreria mido per la gestione MIDI
import pyaudio  # Importa la libreria pyaudio per l'audio
import numpy as np  # Importa la libreria numpy per le operazioni matematiche
import threading  # Importa la libreria threading per la gestione dei thread
import tkinter as tk  # Importa la libreria tkinter per l'interfaccia grafica
from tkinter import ttk  # Importa ttk per i widget di tkinter
from scipy import signal  # Importa la libreria signal da scipy per la generazione del segnale

# Definizione della classe principale
class MidiReceiverApp:
    def __init__(self, root):
        # Inizializza l'applicazione con la finestra principale "root"
        self.root = root
        self.root.title('Synthesizer LB-1 - By Elektronoide')
        self.root.geometry('800x600')

        # Inizializzazione degli oggetti per l'audio
        self.p = pyaudio.PyAudio()
        self.audio_stream = None  # Inizializza self.audio_stream

        # Imposta il volume desiderato (0.0 - 1.0)
        self.volume = 0.5
        self.current_note = None  # Memorizza la nota corrente
        self.current_waveform = 'sinusoide'  # Memorizza la forma d'onda corrente

        # Parametri ADSR (Attack, Decay, Sustain, Release)
        self.attack_time = 0.1
        self.decay_time = 0.1
        self.sustain_level = 0.7
        self.release_time = 0.1

        # Inizializza l'interfaccia utente
        self.init_ui()

    def init_ui(self):
        # Creazione degli elementi dell'interfaccia utente

        # Etichetta per la nota MIDI corrente
        self.note_label = tk.Label(self.root, text="Nota MIDI: ")
        self.note_label.pack()

        # Etichetta per il volume con valore in percentuale
        self.volume_label = tk.Label(self.root, text=f"Volume: {int(self.volume * 100)}%")
        self.volume_label.pack()

        # Slider per regolare il volume
        self.volume_slider = tk.Scale(self.root, from_=0.0, to=1.0, resolution=0.01, orient="horizontal",
        label="Regola il volume", command=self.on_volume_change)
        self.volume_slider.set(self.volume)
        self.volume_slider.pack()

        # Creazione di una cornice per l'envelope ADSR
        envelope_frame = tk.LabelFrame(self.root, text="Envelope ADSR")
        envelope_frame.pack(pady=10, padx=10)

        # Slider per l'Attack all'interno della cornice
        attack_label = tk.Label(envelope_frame, text="Attack:")
        attack_label.pack()
        self.attack_slider = tk.Scale(envelope_frame, from_=0.0, to=2.0, resolution=0.01, orient="horizontal",
        label="Attack (s)", command=self.on_attack_change)
        self.attack_slider.set(self.attack_time)
        self.attack_slider.pack()

        # Slider per il Decay all'interno della cornice
        decay_label = tk.Label(envelope_frame, text="Decay:")
        decay_label.pack()
        self.decay_slider = tk.Scale(envelope_frame, from_=0.0, to=2.0, resolution=0.01, orient="horizontal",
                                     label="Decay (s)", command=self.on_decay_change)
        self.decay_slider.set(self.decay_time)
        self.decay_slider.pack()

        # Slider per il Sustain all'interno della cornice
        sustain_label = tk.Label(envelope_frame, text="Sustain:")
        sustain_label.pack()
        self.sustain_slider = tk.Scale(envelope_frame, from_=0.0, to=1.0, resolution=0.01, orient="horizontal",
                                       label="Sustain", command=self.on_sustain_change)
        self.sustain_slider.set(self.sustain_level)
        self.sustain_slider.pack()

        # Slider per il Release all'interno della cornice
        release_label = tk.Label(envelope_frame, text="Release:")
        release_label.pack()
        self.release_slider = tk.Scale(envelope_frame, from_=0.0, to=2.0, resolution=0.01, orient="horizontal",
        label="Release (s)", command=self.on_release_change)
        self.release_slider.set(self.release_time)
        self.release_slider.pack()

        # Etichetta per il tipo di onda
        waveform_label = tk.Label(self.root, text="Tipo di onda:")
        waveform_label.pack()

        # Opzioni per il tipo di onda
        waveforms = ['sinusoide', 'triangolare', 'quadra', 'dente di sega']  # Aggiunto 'dente di sega'
        self.waveform_var = tk.StringVar()
        self.waveform_menu = ttk.Combobox(self.root, textvariable=self.waveform_var, values=waveforms)
        self.waveform_menu.set(self.current_waveform)
        self.waveform_menu.pack()
        self.waveform_menu.bind('<<ComboboxSelected>>', self.on_waveform_change)

        # Trova le periferiche MIDI disponibili
        midi_devices = mido.get_input_names()
        if midi_devices:
            # Apre la prima periferica MIDI trovata e imposta il callback per i messaggi MIDI
            self.midi_in_port = mido.open_input(midi_devices[0], callback=self.on_midi_message)
            self.midi_device_label = tk.Label(self.root, text=f"Periferica MIDI: {midi_devices[0]}")
            self.midi_device_label.pack()
        else:
            self.midi_in_port = None
            self.midi_device_label = tk.Label(self.root, text="Nessuna periferica MIDI trovata")
            self.midi_device_label.pack()

        # Ottiene l'indice della periferica audio di default
        self.audio_out_device_index = self.p.get_default_output_device_info()['index']
        audio_device_info = self.p.get_device_info_by_index(self.audio_out_device_index)
        self.audio_device_label = tk.Label(self.root, text=f"Periferica audio di default: {audio_device_info['name']}")
        self.audio_device_label.pack()

    # Gestore del messaggio MIDI in arrivo
    def on_midi_message(self, message):
        if message.type == 'note_on':
            note = message.note
            self.note_label.config(text=f"Nota MIDI: {note} ({self.get_note_name(note)})")
            self.current_note = note  # Memorizza la nota corrente
            self.play_note(note, self.current_waveform)
        elif message.type == 'note_off':
            self.stop_audio_generation()

    # Funzione per ottenere il nome della nota MIDI
    def get_note_name(self, note):
        note_names = {
            # Mappa delle note MIDI con i nomi corrispondenti
            21: "LA0", 22: "LA#0", 23: "SI0", 24: "DO1", 25: "DO#1", 26: "RE1", 27: "RE#1", 28: "MI1",
            29: "FA1", 30: "FA#1", 31: "SOL1", 32: "SOL#1", 33: "LA1", 34: "LA#1", 35: "SI1", 36: "DO2",
            37: "DO#2", 38: "RE2", 39: "RE#2", 40: "MI2", 41: "FA2", 42: "FA#2", 43: "SOL2", 44: "SOL#2",
            45: "LA2", 46: "LA#2", 47: "SI2", 48: "DO3", 49: "DO#3", 50: "RE3", 51: "RE#3", 52: "MI3",
            53: "FA3", 54: "FA#3", 55: "SOL3", 56: "SOL#3", 57: "LA3", 58: "LA#3", 59: "SI3", 60: "DO4",
            61: "DO#4", 62: "RE4", 63: "RE#4", 64: "MI4", 65: "FA4", 66: "FA#4", 67: "SOL4", 68: "SOL#4",
            69: "LA4", 70: "LA#4", 71: "SI4", 72: "DO5", 73: "DO#5", 74: "RE5", 75: "RE#5", 76: "MI5",
            77: "FA5", 78: "FA#5", 79: "SOL5", 80: "SOL#5", 81: "LA5", 82: "LA#5", 83: "SI5", 84: "DO6",
            85: "DO#6", 86: "RE6", 87: "RE#6", 88: "MI6", 89: "FA6", 90: "FA#6", 91: "SOL", 92: "SOL#", 108: "DO8",
        }
        return note_names.get(note, "Sconosciuta")

    # Genera un segnale audio a partire dalla frequenza, volume e forma d'onda specificati
    def generate_signal(self, frequency, volume, waveform, duration=1.0):
        t = np.linspace(0, duration, int(44100 * duration), False)
        if waveform == 'sinusoide':
            y = volume * np.sin(2 * np.pi * frequency * t)
        elif waveform == 'triangolare':
            y = volume * (2 * np.arcsin(np.sin(2 * np.pi * frequency * t)) / np.pi)
        elif waveform == 'quadra':
            y = volume * np.sign(np.sin(2 * np.pi * frequency * t))
        elif waveform == 'dente di sega':  # Aggiunto 'dente di sega'
            y = volume * signal.sawtooth(2 * np.pi * frequency * t)
        else:
            y = np.zeros(len(t))
        return y

    # Riproduce una nota con la frequenza e la forma d'onda specificate
    def play_note(self, note, waveform='sinusoide'):
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()

        if self.current_note is not None:
            frequency = self.note_to_frequency(note)
            envelope = self.generate_envelope()
            y = self.generate_signal_with_envelope(frequency, envelope, waveform)
            self.play_audio(y)

    # Ferma la generazione audio corrente
    def stop_audio_generation(self):
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()

    # Converte una nota MIDI in frequenza
    def note_to_frequency(self, note):
        return 440.0 * (2 ** ((note - 69) / 12.0))

    # Riproduce l'audio a partire dai dati audio forniti
    def play_audio(self, audio_data):
        stream = None  # Dichiarare stream qui

        def play_audio_thread():
            nonlocal stream
            stream = self.p.open(format=pyaudio.paFloat32, channels=1, rate=44100, output=True,
                                 output_device_index=self.audio_out_device_index)
            stream.write(audio_data.tobytes())
            stream.stop_stream()
            stream.close()

        audio_thread = threading.Thread(target=play_audio_thread)
        audio_thread.start()
        self.audio_stream = stream  # Aggiornare anche qui

    # Gestore del cambio di volume
    def on_volume_change(self, volume):
        self.volume = float(volume)
        self.volume_label.config(text=f"Volume: {int(self.volume * 100)}%")

    # Gestori del cambio dei parametri ADSR
    def on_attack_change(self, attack):
        self.attack_time = float(attack)

    def on_decay_change(self, decay):
        self.decay_time = float(decay)

    def on_sustain_change(self, sustain):
        self.sustain_level = float(sustain)

    def on_release_change(self, release):
        self.release_time = float(release)

    # Gestore del cambio della forma d'onda
    def on_waveform_change(self, event):
        selected_waveform = self.waveform_var.get()
        self.current_waveform = selected_waveform
        if self.current_note is not None:
            self.play_note(self.current_note, selected_waveform)

    # Genera un envelope ADSR
    def generate_envelope(self):
        envelope_length = int(44100 * (self.attack_time + self.decay_time + self.release_time))
        envelope = np.zeros(envelope_length)

        attack_samples = int(44100 * self.attack_time)
        decay_samples = int(44100 * self.decay_time)
        release_samples = int(44100 * self.release_time)

        # Attack
        envelope[:attack_samples] = np.linspace(0, 1, attack_samples)

        # Decay
        envelope[attack_samples:attack_samples + decay_samples] = np.linspace(1, self.sustain_level, decay_samples)

        # Sustain
        envelope[attack_samples + decay_samples:-release_samples] = self.sustain_level

        # Release
        envelope[-release_samples:] = np.linspace(self.sustain_level, 0, release_samples)

        return envelope

    # Genera un segnale audio con envelope
    def generate_signal_with_envelope(self, frequency, envelope, waveform):
        duration = len(envelope) / 44100
        t = np.linspace(0, duration, len(envelope), False)
        signal = self.generate_signal(frequency, self.volume, waveform, duration)
        return signal * envelope

if __name__ == '__main__':
    # Creazione della finestra principale dell'applicazione
    root = tk.Tk()
    app = MidiReceiverApp(root)
    root.mainloop()

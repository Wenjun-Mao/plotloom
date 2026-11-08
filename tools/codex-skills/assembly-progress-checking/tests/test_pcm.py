"""Test the production PCM verifier directly, without creating exports."""
from pathlib import Path
import sys
import tempfile
import unittest
import wave

PROJECT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT / '.local/ref2va/manager'))
from assembly_timeline import slot_plan, TimelineError
from assembly_audio import write_ordered_wav, verify_ordered_wav


class PcmTests(unittest.TestCase):
    def test_offsets_prefix_and_zero_tail(self):
        def source(name, count):
            proof = {'frames': 1, 'pcmSamples': count, 'sha256': name,
                     **slot_plan(1, count)}
            return (name, b'\x01\x02\x03\x04' * count, proof)
        sources = [source('a', 1320), source('b', 1330)]
        with tempfile.TemporaryDirectory() as d:
            wav = Path(d) / 'a.wav'
            result = write_ordered_wav(wav, sources)
            self.assertEqual(result['segments'][1]['sampleOffset'], result['segments'][0]['slotCount'])
            self.assertEqual(result['newZeroSamples'], 18)
            self.assertEqual(verify_ordered_wav(wav, sources, result['segments']), result)
            rows = [dict(r) for r in result['segments']]
            rows[1]['sampleOffset'] += 1
            with self.assertRaises(TimelineError):
                verify_ordered_wav(wav, sources, rows)
            with wave.open(str(wav), 'rb') as f:
                pcm = f.readframes(f.getnframes())
            with wave.open(str(wav), 'wb') as f:
                f.setnchannels(2)
                f.setsampwidth(2)
                f.setframerate(32000)
                f.writeframes(pcm + bytes(4))
            with self.assertRaises(TimelineError):
                verify_ordered_wav(wav, sources, result['segments'])
            # Also reject a changed native sample.
            data = bytearray(wav.read_bytes())
            data[44] ^= 1
            wav.write_bytes(data)
            with self.assertRaises(TimelineError):
                verify_ordered_wav(wav, sources, result['segments'])


if __name__ == '__main__':
    unittest.main()

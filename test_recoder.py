import unittest
import recoder

class TestRecoder(unittest.TestCase):
    
    def test_output_path(self):
        self.assertEqual(recoder.output_path('/','foo.m2t'), '/foo.m2t')
        self.assertEqual(recoder.output_path('/tmp','foo.m2t'), '/tmp/foo.m2t')
        self.assertEqual(recoder.output_path('/tmp/','foo.m2t'), '/tmp/foo.m2t')
        self.assertEqual(recoder.output_path('/tmp/','/film/foo.m2t'), '/tmp/foo.m2t')
        self.assertEqual(recoder.output_path('.mkv','foo.m2t'), 'foo.mkv')
        self.assertEqual(recoder.output_path('.mkv','/film/foo.m2t'), '/film/foo.mkv')
        self.assertEqual(recoder.output_path('/tmp/.mkv','foo.m2t'), '/tmp/foo.mkv')
        self.assertEqual(recoder.output_path('/tmp/.mkv','/film/foo.m2t'), '/tmp/foo.mkv')
        self.assertEqual(recoder.output_path('+.mkv','foo.m2t'), 'foo.mkv')
        self.assertEqual(recoder.output_path('+.mkv','/film/foo.m2t'), '/film/foo.mkv')

    def test_parse_streams(self):
        # Kaffeine DVB-T recording
        test1 = '''Stream #0:0[0xd3]: Video: h264 (High) ([27][0][0][0] / 0x001B), yuv420p(tv, bt470bg), 704x576 [SAR 16:11 DAR 16:9], 25 fps, 50 tbr, 90k tbn, 50 tbc
Stream #0:1[0xdd](dan): Audio: aac_latm (HE-AAC) ([17][0][0][0] / 0x0011), 48000 Hz, stereo, fltp
Stream #0:2[0xe7](dan): Subtitle: dvb_teletext ([6][0][0][0] / 0x0006)
Stream #0:3[0xeb](dan): Subtitle: dvb_subtitle ([6][0][0][0] / 0x0006)
Stream #0:4[0xec](dan): Subtitle: dvb_subtitle ([6][0][0][0] / 0x0006) (hearing impaired)'''
        result1 = [{'type': 'video', 'index': '0'}, {'type': 'audio', 'desc': 'aac_latm (HE-AAC) ([17][0][0][0] / 0x0011), 48000 Hz, stereo, fltp', 'index': '1'}, {'type': 'subtitle', 'index': '3'}]
        self.assertEqual(recoder.parse_streams(test1), result1)
        
        # probe handbrake-ripped dvd
        test2 = '''Stream #0:0(eng): Video: h264 (High), yuv420p(tv, smpte170m/smpte170m/bt709), 706x300 [SAR 8:9 DAR 1412:675], SAR 127:143 DAR 44831:21450, 23.98 fps, 23.98 tbr, 1k tbn, 180k tbc (default)
Stream #0:1(eng): Audio: aac (LC), 48000 Hz, mono, fltp (default)
Stream #0:2(eng): Audio: ac3, 48000 Hz, mono, fltp, 192 kb/s
Stream #0:3(eng): Subtitle: subrip'''
        result2 = [{'type': 'video', 'index': '0'}, {'type': 'audio', 'desc': 'aac (LC), 48000 Hz, mono, fltp (default)', 'index': '1'}, {'type': 'audio', 'desc': 'ac3, 48000 Hz, mono, fltp, 192 kb/s', 'index': '2'}, {'type': 'subtitle', 'index': '3'}]
        self.assertEqual(recoder.parse_streams(test2), result2)
        
        # Sony A5000 (MTS)        
        test3 = '''Stream #0:0[0x1011]: Video: h264 (High) (HDMV / 0x564D4448), yuv420p(top first), 1920x1080 [SAR 1:1 DAR 16:9], 25 fps, 25 tbr, 90k tbn, 50 tbc
Stream #0:1[0x1100]: Audio: ac3 (AC-3 / 0x332D4341), 48000 Hz, stereo, fltp, 256 kb/s
Stream #0:2[0x1200]: Subtitle: hdmv_pgs_subtitle ([144][0][0][0] / 0x0090), 1920x1080'''
        result3 = [{'type':'video', 'index':'0'},{'type':'audio', 'index':'1', 'desc':'ac3 (AC-3 / 0x332D4341), 48000 Hz, stereo, fltp, 256 kb/s'}]
        self.assertEqual(recoder.parse_streams(test3), result3)


    def test_concat_list(self):
        # concat list with null output
        inputs = ['/tmp/foo.mkv', '/tmp/bar.mkv']
        outputPath = None
        
        (output, list) = recoder.concat_list(outputPath, inputs)
        self.assertEqual(output, 'concat.mkv')
        self.assertEqual(list, ["file '/tmp/foo.mkv'", "file '/tmp/bar.mkv'"])
    
    def test_to_seconds(self):
        self.assertEqual(recoder.to_seconds('01:05:27'), 3600+300+27)
        self.assertEqual(recoder.to_seconds('05:00'), 300)
        self.assertEqual(recoder.to_seconds('27'), 27)
        self.assertEqual(recoder.to_seconds('01:90'), 60+90)

    def test_from_seconds(self):
        self.assertEqual(recoder.from_seconds(3600+300+27), '01:05:27')
        self.assertEqual(recoder.from_seconds(300), '00:05:00')
        self.assertEqual(recoder.from_seconds(27), '00:00:27')
        self.assertEqual(recoder.from_seconds(60+90), '00:02:30') 
        
if __name__ == '__main__':
    unittest.main()

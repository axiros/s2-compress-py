// Writes ../data/go-s2.json and ../data/go-s2-big.json: payloads and their S2 blocks from Go's klauspost/compress/s2
// (s2.Encode, s2.EncodeBetter), for the compatibility tests. The payloads are made up, no
// device data. Run: cd tests/go-vector && go run .
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"math/rand/v2"
	"os"

	"github.com/klauspost/compress/s2"
)

// values is a TR-181-like raw value set, path -> value, about size bytes
func values(size int, seed uint64) []byte {
	r := rand.New(rand.NewPCG(seed, 1))
	m := map[string]string{}
	for i := 1; ; i++ {
		p := fmt.Sprintf("Device.WiFi.AccessPoint.%d.AssociatedDevice.%d.", i%8+1, i)
		m[p+"MACAddress"] = fmt.Sprintf("02:00:%02x:%02x:%02x:%02x", r.IntN(256), r.IntN(256), r.IntN(256), r.IntN(256))
		m[p+"SignalStrength"] = fmt.Sprint(-30 - r.IntN(60))
		m[p+"Stats.BytesSent"] = fmt.Sprint(r.IntN(1 << 30))
		m[p+"Active"] = "true"
		if b, _ := json.Marshal(m); len(b) >= size {
			return b[:size]
		}
	}
}

func main() {
	random := make([]byte, 1024)
	r := rand.New(rand.NewPCG(7, 7))
	for i := range random {
		random[i] = byte(r.IntN(256))
	}
	payloads := map[string][]byte{
		"empty":     {},
		"one":       []byte("x"),
		"random1k":  random,
		"tr181-4k":  values(4096, 1),
		"tr181-64k": values(65536, 2),
	}
	type entry struct {
		Payload []byte `json:"payload"`
		Encode  []byte `json:"encode"`
		Better  []byte `json:"better"`
	}
	out := map[string]entry{}
	for name, p := range payloads {
		out[name] = entry{p, s2.Encode(nil, p), s2.EncodeBetter(nil, p)}
	}
	b, _ := json.MarshalIndent(out, "", " ")
	if err := os.WriteFile("../data/go-s2.json", b, 0o644); err != nil {
		panic(err)
	}
	// a block above 16 MiB, where minlz 1.2.3 cannot encode: Go's block must decode. The
	// payload repeats a pattern, so the test makes it anew and the block is small
	pattern := []byte("Device.WiFi.Radio.1.Channel=36;")
	size := 59 << 20
	big := bytes.Repeat(pattern, size/len(pattern)+1)[:size]
	b, _ = json.MarshalIndent(map[string]any{"pattern": string(pattern), "size": size,
		"encode": s2.Encode(nil, big)}, "", " ")
	if err := os.WriteFile("../data/go-s2-big.json", b, 0o644); err != nil {
		panic(err)
	}
}

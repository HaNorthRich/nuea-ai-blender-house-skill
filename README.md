# nuea.ai Blender House — Skill ปั้นบ้าน 3D ใน Blender ด้วย Claude

> **For Claude and other AI agents:** to install this skill, follow [INSTALL.md](INSTALL.md)
> (raw: https://raw.githubusercontent.com/HaNorthRich/nuea-ai-blender-house-skill/main/INSTALL.md).

## ติดตั้งง่ายที่สุด: ให้ Claude ลงให้

1. ลง [Blender](https://www.blender.org/download/) (4.2 ขึ้นไป) และเปิด [Claude Code](https://claude.com/claude-code)
   (ในแอป Claude บนคอมพิวเตอร์ แท็บ Code หรือใน terminal) Claude Code ใช้กับแพ็กเกจเสียเงินของ Claude (Pro ขึ้นไป)
   หรือ API key แพ็กเกจฟรีใช้ไม่ได้ ([ดูแพ็กเกจ](https://claude.com/pricing))
2. ส่งข้อความนี้ให้ Claude

   ```
   ลง Skill นี้ให้หน่อย https://github.com/HaNorthRich/nuea-ai-blender-house-skill
   ```

3. Claude จะเช็ก Blender ลง Skill และต่อ Blender MCP ให้ตามขั้นตอนใน [INSTALL.md](INSTALL.md) ในโหมดปกติ
   Claude Code จะขอให้คุณกดอนุญาตก่อนรันแต่ละคำสั่ง อ่านคำสั่งก่อนกด Allow และ INSTALL.md สั่งให้ Claude ถามคุณก่อน
   ติดตั้งโปรแกรมเพิ่ม
4. ตอนจบ Claude จะบอกสิ่งที่คุณต้องทำเอง:
   - เปิด add-on "MCP for Blender" ใน Blender แล้วกด Start MCP Server ถ้ายังไม่ทำงาน
   - ปิด Claude Code ให้สนิทแล้วเปิดใหม่
   - พิมพ์ `เช็กสถานะ Blender` ถ้า Claude ตอบเวอร์ชันของ Blender ได้ แปลว่าพร้อมใช้

ถ้าอยากลงเอง ดูหัวข้อ [ติดตั้ง](#ติดตั้ง) ด้านล่าง

## Skill นี้ทำอะไร

Skill สำหรับ [Claude Code](https://claude.com/claude-code) ที่ช่วยให้ Claude ปั้นบ้านใน Blender ผ่าน Blender MCP ทำได้ 2 แบบ

1. **โมเดลขาย**: จากแปลน, brochure หรือภาพ SketchUp → ผนัง ช่องเปิด หลังคา กระเบื้อง วัสดุ เฟอร์นิเจอร์ แสง
   ภาพ render และผังพื้นมุมบน
2. **โมเดลก่อสร้าง**: ปั้นทีละขั้นตามลำดับงานจริง แต่ละชิ้นทำขนาดจริงตามสินค้า เพื่อเอาปริมาณไปทำ BOQ
   ลำดับขั้นมีดังนี้
   - ฐานราก → ตอม่อ → คานคอดิน → พื้น → เสา
   - ผนัง → หลังคา → ฝ้า
   - สีรองพื้น → สีรอบ 1 → กระเบื้อง → ไฟฟ้า → สีรอบ 2
   - ประตูหน้าต่าง

   ทุกขั้นมีตัวตรวจ (selfcheck) ที่อ่านค่ากลับจากโมเดล และมีเทสแบบ "จงใจทำผิด" ที่ตัวตรวจต้องจับได้

ความรู้ในชุดนี้กลั่นจากงานจริง ทุกข้อในไฟล์คือบทเรียนที่เคยพลาดมาแล้วอย่างน้อยหนึ่งครั้ง

## พิสูจน์ได้: บ้านตัวอย่างสร้างได้ทั้งหลังในคำสั่งเดียว

ในชุดมีโค้ดของบ้านตัวอย่าง E42 (บ้านชั้นเดียว 42 ตร.ม.) ครบทุกขั้น สร้างจาก Blender เปล่าได้ในราว 2 นาที
ระหว่างสร้าง ตัวตรวจของทุกขั้นต้องผ่าน

```bash
cd nuea-ai-blender-house/examples/e42/scripts
blender -b --factory-startup --python-exit-code 1 -P build_all.py      # → ../e42_house.blend
```

ปริมาณที่ได้มีตัวอย่างดังนี้:

| หมวด | ปริมาณ |
|---|---|
| อิฐมอญ | 3,761 ก้อน |
| หลังคา | กระเบื้อง CPAC 81.5 ตร.ม. |
| สี | ผนังใน 96.7 ตร.ม. · นอก 63.3 ตร.ม. |
| พื้น | กระเบื้อง 36.1 ตร.ม. |
| ไฟฟ้า | ดาวน์ไลท์ 12 · สวิตช์ 7 · ปลั๊ก 9 · ท่อ 3/4" 76.7 ม. · 1/2" 31.2 ม. |
| ประตูหน้าต่าง | ประตู 5 ชุด · หน้าต่างอลูมิเนียม 7 ชุด |

## ต้องมีอะไรบ้าง

- Claude Code
- Blender 4.2 ขึ้นไป (ทดสอบบน 5.2.1) คำสั่ง `blender` ในหน้านี้บน Mac คือ
  `/Applications/Blender.app/Contents/MacOS/Blender` (หรือตั้ง alias ไว้)
- [uv](https://docs.astral.sh/uv/) (ใช้คำสั่ง `uvx`)
- [MCP for Blender](https://github.com/ahujasid/blender-mcp) ที่ต่อ Claude Code เข้ากับ Blender

## ติดตั้ง

```bash
# 1. Skill
git clone https://github.com/HaNorthRich/nuea-ai-blender-house-skill.git
mkdir -p ~/.claude/skills
cp -R nuea-ai-blender-house-skill/nuea-ai-blender-house ~/.claude/skills/

# 2. Blender MCP: add-on ฝั่ง Blender และ server ฝั่ง Claude Code (ใช้ได้ทุกโปรเจกต์)
uvx mcp-for-blender install-addon
claude mcp add --scope user blender "$(command -v uvx)" mcp-for-blender   # (path เต็มของ uvx: แอปบนเดสก์ท็อปหาเจอด้วย)
# Windows: ใช้ path ที่ `where uvx` พิมพ์ (C:\…\uvx.exe) แทน "$(command -v uvx)"
```

เปิด Blender แล้วเปิด add-on และกด Start MCP Server จากนั้นเปิด Claude Code ใหม่ แล้วสั่งว่า "เช็กสถานะ Blender"
ถ้า Claude ตอบเวอร์ชันของ Blender ได้ แปลว่าต่อกันแล้ว Skill จะโหลดเองเมื่อสั่งงานที่เกี่ยวข้อง

## ลองสั่งแบบนี้

- "ปั้น 3D บ้านจากแปลนนี้ใน Blender หลังคาปั้นหยา กระเบื้องลอน แล้ว render ภาพขาย 4 มุม" (แนบแปลน)
- "ทำโมเดลบ้านใน Blender ตามภาพ SketchUp นี้ ใส่เฟอร์นิเจอร์และวัสดุจาก Poly Haven"
- "ปั้นตามลำดับก่อสร้าง เริ่มจากฐานราก ผมจะส่งสเปกให้ทีละขั้น"

Claude จะถามสเปกของแต่ละขั้นก่อนปั้น (สินค้า ขนาด สี ตำแหน่ง) ปั้นทีละขั้น ตรวจ แล้วหยุดให้คุณดูก่อนไปขั้นถัดไป

## ในชุดมีอะไร

| ที่อยู่ | คืออะไร |
|---|---|
| `nuea-ai-blender-house/SKILL.md` | ขั้นตอนหลัก: โมเดลขาย (Workflow A) และโมเดลก่อสร้างทีละขั้น (Workflow B) |
| `nuea-ai-blender-house/references/` | ความรู้แยกตามขั้น: โครงสร้าง ผนัง หลังคา ฝ้า สี กระเบื้อง ไฟฟ้า ประตูหน้าต่าง และวิธีตรวจ |
| `nuea-ai-blender-house/scripts/` | สคริปต์ Blender: ผนัง/ช่องเปิด หลังคา ครอบ CPAC เหล็กรูปพรรณตามหน้าตัดจริง ตรวจคาน (WSD) วาดแบบ CAD render ส่งออก SketchUp คลังเฟอร์นิเจอร์ (CC0/CC-BY) วางบ้านลงผังโครงการ |
| `nuea-ai-blender-house/examples/e42/` | บ้านตัวอย่าง: โมดูลทีละขั้น, `build_all.py`, เทสทุกชุด, spec ของงานไฟฟ้าและประตูหน้าต่าง |

## ข้อควรรู้

- ภาพ render เป็นภาพจำลองเพื่อการโฆษณา
- ปริมาณจากโมเดลต้องให้ผู้รู้ตรวจก่อนใช้สั่งของจริง และค่าที่ Claude สมมติไว้ต้องยืนยันก่อนเสมอ
- สคริปต์ตรวจคานใช้เลือกจากแบบที่มีอยู่เพื่อทำโมเดลและ BOQ เท่านั้น งานออกแบบโครงสร้างจริงต้องให้วิศวกรผู้มีใบอนุญาตลงนาม
- ชื่อสินค้าและยี่ห้อในไฟล์เป็นตัวอย่างจากงานจริง เปลี่ยนตามงานของคุณได้ ในชุดไม่มีราคา

## English

A Claude Code skill for modelling houses in Blender through Blender MCP: sales models (walls, openings, roofs,
materials, furniture, renders) or construction models built stage by stage in real construction order, every piece
at its product's size, each stage read back by a selfcheck and guarded by a mutation test suite. The full worked
example (a 42 m² house, `examples/e42/`) builds from an empty Blender with every check passing:
`blender -b --factory-startup --python-exit-code 1 -P nuea-ai-blender-house/examples/e42/scripts/build_all.py`.
Easiest install: send this repository's link to Claude Code and ask it to install the skill; it follows
[INSTALL.md](INSTALL.md). By hand: copy `nuea-ai-blender-house/` into
`~/.claude/skills/` (`mkdir -p ~/.claude/skills` first), then connect Blender: `uvx mcp-for-blender install-addon` and
`claude mcp add --scope user blender "$(command -v uvx)" mcp-for-blender` (Windows: the `C:\…\uvx.exe` path that
`where uvx` prints). Claude Code needs a paid Claude plan
(Pro and up) or an API key. Quantities need a qualified check before ordering; structural design needs a licensed engineer.

---

MIT License · by [nuea.ai](https://github.com/HaNorthRich)

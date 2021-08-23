MEMORY
{
  FLASH  (rwx)  : ORIGIN = 0x00000000, LENGTH = 1M 
  RAM    (rwx)  : ORIGIN = 0x20000000, LENGTH = 16K
}

ENTRY(_start)

SECTIONS
{
  .boot :
  {
    LONG(ORIGIN(RAM) + LENGTH(RAM));
    LONG(_start);
    . = ALIGN(128);
  } > FLASH

  .text :
  {
    *(.text*)
  } > FLASH 

  .rodata :
  {
    *(.rodata*)
  } > FLASH 

  .data :
  {
    *(.data*)
  }

  .bss ALIGN(4):
  {
    *(.bss*)
  } > RAM

  /DISCARD/ :
  {
	  *(.ARM.exidx*);
  }
}
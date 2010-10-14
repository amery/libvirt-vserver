#include <config.h>

#include "internal.h"
#include "driver.h"

#include "vserver_driver.h"

static virDriver vserverDriver = {
    .no = VIR_DRV_VSERVER,
    .name = "VServer",
};

#ifdef WITH_LIBVIRTD
static virStateDriver vserverStateDriver = {
    .name = "VServer",
};
#endif

int
vserverRegister(void)
{
    virRegisterDriver(&vserverDriver);
#ifdef WITH_LIBVIRTD
    virRegisterStateDriver(&vserverStateDriver);
#endif
    return 0;
}

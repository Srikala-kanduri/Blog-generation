import { fetchPendingOrder, getCurrentUserId, getPickupAddress, updateCart } from "@/services/orderservice";
import { FontAwesome, Ionicons } from "@expo/vector-icons";
import DateTimePicker, { DateTimePickerAndroid } from '@react-native-community/datetimepicker';
import { useFonts } from "expo-font";
import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useEffect, useRef, useState } from 'react';
import { Dimensions, FlatList, Image, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from "react-native-safe-area-context"; // ✅ Added
import ShimmerSkeleton from "../../components/ShimmerSkeleton";
// add these to the top with your other imports
import * as Location from 'expo-location';
import { ActivityIndicator, Alert } from 'react-native';

const { width, height } = Dimensions.get("window");

export default function CartScreen() {
  const router = useRouter();
  const [loading, setLoading] = useState<boolean>(true);
 const { selectedItems, newAddress } = useLocalSearchParams<{
  selectedItems?: string;
  newAddress?: string;
}>();

  const [fontsLoaded] = useFonts({
    "LeagueSpartan-Regular": require("../../assets/fonts/static/LeagueSpartan-Regular.ttf"),
    "LeagueSpartan-Bold": require("../../assets/fonts/static/LeagueSpartan-Bold.ttf"),
    "LeagueSpartan-Medium": require("../../assets/fonts/static/LeagueSpartan-Medium.ttf"),
  });

  const parsedItems = selectedItems ? JSON.parse(selectedItems as string) : [];
  const [items, setItems] = useState<CartItem[]>(
    parsedItems.map((item: any, index: number) => ({
      id: String(index + 1),
      name: item.item_name ?? item.name,
      unitPrice: Number(item.unit_price ?? item.price ?? 0), // <- use unitPrice
      qty: Number(item.quantity ?? item.qty ?? 1),
    }))
  );

  const [pickupDate, setPickupDate] = useState(new Date());
  const [pickupTime, setPickupTime] = useState(new Date());
  const [date, setDate] = useState<Date | null>(null);
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [time, setTime] = useState<Date | null>(null);
  const [showTimePicker, setShowTimePicker] = useState(false);

  const showDatePickerFunc = () => {
    DateTimePickerAndroid.open({
      value: pickupDate || new Date(),
      mode: 'date',
      is24Hour: true,
      onChange: (event, selectedDate) => {
        if (selectedDate) setPickupDate(selectedDate);
      },
    });
  };

  const showTimePickerFunc = () => {
    DateTimePickerAndroid.open({
      value: pickupTime || new Date(),
      mode: 'time',
      is24Hour: true,
      onChange: (event, selectedTime) => {
        if (selectedTime) setPickupTime(selectedTime);
      },
    });
  };
  const [orderId, setOrderId] = useState<string | null>(null);
  const [showBill, setShowBill] = useState(false);
 const [pickupAddress, setPickupAddress] = useState("");
const [savedAddresses, setSavedAddresses] = useState<string[]>([]);

useEffect(() => {
  async function loadAddress() {
    try {
      // get the primary address your service returns (registered default)
      const regAddr = await getPickupAddress();

      if (regAddr) {
        setPickupAddress(prev => prev || regAddr);
         setSavedAddresses(prev => {
          // put the registered address first, avoid dupes if prev already contains it
          const normalizedPrev = prev.map(a => a.trim());
          if (normalizedPrev.includes(regAddr.trim())) {
            // Move regAddr to the front while preserving the rest order
            return [regAddr, ...prev.filter(a => a.trim() !== regAddr.trim())];
          }
          // Prepend the registration address so it is always first
          return [regAddr, ...prev];
        });
      } else {
        // if no single default address, you could fetch full list here
        // const list = await getSavedAddresses(); setSavedAddresses(list || []);
      }
    } catch (err) {
      console.error("loadAddress failed", err);
    }
  }
  loadAddress();
}, []);

useEffect(() => {
  if (!newAddress) return;

  const addr = (newAddress as string).trim();
  if (!addr) return;

  // 1) show this under "Pickup from Home"
  setPickupAddress(addr);

  // 2) add it into Saved Addresses (after registration address)
  setSavedAddresses((prev) => {
    if (prev.some((a) => a.trim() === addr)) {
      return prev; // already there
    }

    if (prev.length === 0) {
      return [addr];
    }

    const reg = prev[0];       // keep first as registered/default
    const rest = prev.slice(1);
    return [reg, ...rest, addr];
  });
}, [newAddress]);


  const [showPickupOptions, setShowPickupOptions] = useState(false);
const [locLoading, setLocLoading] = useState(false);

  const itemTotal = items.reduce((sum, item) => sum + item.unitPrice * item.qty, 0);
  const handlingCharge = 0;
  const deliveryCharge = 0;
  const totalPay = itemTotal + handlingCharge + deliveryCharge;

  type CartItem = {
    id: string;
    name: string;
    unitPrice: number;
    qty: number;
  };

  const loadOrders = async () => {
    setLoading(true);
    try {
      const data = await fetchPendingOrder();
      if (data) {
        setOrderId(data.id); // ✅ save the orderId
        const formatted = (data.items || []).map((item: any, i: number) => ({
          id: String(i + 1),
          name: item.item_name,
          unitPrice: Number(item.unit_price ?? item.price ?? item.finalPrice ?? 0), // <- important
          qty: Number(item.quantity ?? 1),
        }));
        setItems(formatted);
      } else {
        setItems([]);
      }
    } catch (err) {
      console.error(err);
      setItems([]);
    } finally {
      setLoading(false);
    }
  };
  
useEffect(() => {
  loadOrders();
}, []);

// assumes items: CartItem[] in scope and updateCart/getCurrentUserId are available
const inFlightRef = useRef<Record<string, boolean>>({}); // keep outside function (top of component)

const updateQty = async (id: string, delta: number) => {
  // prevent concurrent updates for the same item
  if (inFlightRef.current[id]) {
    console.log(`update for ${id} already in flight — ignoring`);
    return;
  }
  inFlightRef.current[id] = true;

  // preserve previous state for rollback
  const prevItems = items;

  // produce updated list (including zeros)
  const updatedAll = items.map((item: CartItem) =>
    item.id === id ? { ...item, qty: Math.max(0, item.qty + delta) } : item
  );

  // UI: remove zero-qty items immediately for user (optimistic)
  const newItemsForUI = updatedAll.filter((item: CartItem) => item.qty > 0);
  setItems(newItemsForUI);

  // Find changed item (send to backend)
  const changed = updatedAll.find((item: CartItem) => item.id === id);
  if (!changed) {
    inFlightRef.current[id] = false;
    return;
  }

  // Build payload for backend (Solution A)
  const payload = [
    {
      item_name: String(changed.name),
      price: Number(changed.unitPrice ?? 0),
      quantity: Number(changed.qty), // if 0 → backend removes item
    },
  ];

  try {
    const userId = await getCurrentUserId();
    if (!userId) {
      alert("Please log in to continue");
      // rollback
      setItems(prevItems);
      inFlightRef.current[id] = false;
      return;
    }

    // send ONLY changed item to backend
    const res = await updateCart(userId, payload);

    // if updateCart returns the updated order (recommended), use it as source of truth:
    if (res && res.items && Array.isArray(res.items)) {
      const serverItems = res.items.map((it: any) => ({
        id: it.id ?? it.item_name,
        name: it.item_name,
        qty: Number(it.quantity),
        unitPrice: Number(it.unit_price ?? it.price ?? it.finalPrice ?? 0), // ← FIXED
      })) as CartItem[];
      
      setItems(serverItems);
      inFlightRef.current[id] = false;
      return;
    }

    // if res is null or doesn't include items, treat as failure and rollback
    if (!res) {
      console.warn("Server update returned null — rolling back UI");
      setItems(prevItems);
    }
  } catch (err) {
    console.error("updateCart failed, rolling back", err);
    // rollback
    setItems(prevItems);
  } finally {
    // clear in-flight marker
    inFlightRef.current[id] = false;
  }
};
const useMyCurrentLocation = async () => {
  try {
    setLocLoading(true);

    // request foreground permission
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert(
        "Location permission required",
        "Please allow location access to use this feature."
      );
      setLocLoading(false);
      return;
    }

    // get current position
    const pos = await Location.getCurrentPositionAsync({
      accuracy: Location.Accuracy.Balanced,
    });

    const { latitude, longitude } = pos.coords;

    // reverse geocode to human-readable address (expo-location)
    const places = await Location.reverseGeocodeAsync({ latitude, longitude });
    const place = places && places.length > 0 ? places[0] : null;

    let addr = "";
    if (place) {
      const parts = [
        place.name,
        place.street,
        place.subregion,
        place.city,
        place.region,
        place.postalCode,
        place.country,
      ].filter(Boolean);
      addr = parts.join(", ");
    } else {
      addr = `Lat: ${latitude.toFixed(5)}, Lon: ${longitude.toFixed(5)}`;
    }

    // 1) update bottom bar immediately
    setPickupAddress(addr);

    // 2) append the new address AFTER the registration address (index 0)
    setSavedAddresses(prev => {
      if (!addr) return prev;

      const normalizedNew = addr.trim();
      // if it already exists, do nothing
      if (prev.some(a => a.trim() === normalizedNew)) return prev;

      if (prev.length === 0) {
        // no registration address present yet, this becomes the first saved address
        return [addr];
      }

      // preserve registration address at index 0 and any addresses in between,
      // then append new address to the end
      const reg = prev[0];
      const rest = prev.slice(1);
      return [reg, ...rest, addr];
    });

    // OPTIONAL: persist new saved address to backend (uncomment & implement)
    // try {
    //   const userId = await getCurrentUserId();
    //   if (userId) {
    //     await saveAddressForUser(userId, { address: addr, latitude, longitude });
    //   }
    // } catch (e) {
    //   console.warn("persist saved address failed", e);
    // }

    // close the sheet (or remove this if you want to keep sheet open for confirmation)
    setShowPickupOptions(false);

  } catch (err) {
    console.error("useMyCurrentLocation error:", err);
    Alert.alert("Unable to fetch location", "Please try again or add address manually.");
  } finally {
    setLocLoading(false);
  }
};


const renderItem = ({ item }: { item: CartItem }) => (
    <View style={styles.row}>
      <Text style={styles.itemName}>{item.name}</Text>
      <View style={styles.qtyContainer}>
        <TouchableOpacity disabled={loading} onPress={() => updateQty(item.id, -1)} style={styles.qtyButton}>
          <Text style={styles.qtySymbol}>−</Text>
        </TouchableOpacity>
        <Text style={styles.qtyText}>{item.qty}</Text>
        <TouchableOpacity disabled={loading} onPress={() => updateQty(item.id, 1)} style={styles.qtyButton}>
          <Text style={styles.qtySymbol}>+</Text>
        </TouchableOpacity>
      </View>
      <Text style={styles.itemPrice}>₹{(item.unitPrice * item.qty).toFixed(0)}/-</Text>
    </View>
  );

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#fff" }}> 
      <View style={{ flex: 1 }}>
        {/* Header */}
        <View style={styles.header}>
        <TouchableOpacity
  style={styles.backBtn}
  onPress={() => {
    if (!items || items.length === 0) {
      router.push("/(tabs)"); // cart empty → go to index
    } else {
      router.push({
        pathname: "/(tabs)",
        params: { selectedItems: JSON.stringify(items) }, // cart has items
      });
    }
  }}
>
  <Ionicons name="arrow-back" size={26} color="black" />
</TouchableOpacity>
          <Text style={styles.headerTitle}>Cart</Text>
        </View>
        {loading ? (
  <View style={{ padding: width * 0.04 }}>
    <ShimmerSkeleton height={60} style={{ marginBottom: 15 }} />
    <ShimmerSkeleton height={60} style={{ marginBottom: 15 }} />
    <ShimmerSkeleton height={60} style={{ marginBottom: 15 }} />
  </View>
        ): items.length === 0 ? (
          // Empty-cart UI
          <View style={styles.emptyContainer}>
            <View style={styles.emptyCard}>
            <View style={styles.iconWrapper}>
            <Image source={require('../../assets/images/cart-image.jpg')} style={styles.cartIcon} />
            </View>
              <Text style={styles.emptyText}>Your cart is empty</Text>
              <TouchableOpacity
                style={styles.addClothesButton}
                onPress={() =>
                  router.push({
                    pathname: "/category",
                    params: { selectedItems: JSON.stringify(items) }, // send current cart items
                  })
                }
              >
                <Text style={styles.addClothesText}>Add Clothes</Text>
              </TouchableOpacity>
            </View>
          </View>
        ) : (
          <>
            <View style={styles.container}>
              <ScrollView
                contentContainerStyle={{ paddingBottom: height * 0.17 }}
                showsVerticalScrollIndicator={false}
              >
                {/* Cart Card */}
                <View style={styles.card}>
                  <View style={styles.tableHeader}>
                    <Text style={[styles.headerText, { flex: 2, textAlign: 'left' }]}>Items</Text>
                    <Text style={[styles.headerText, { flex: 1, textAlign: 'center' }]}>Qty</Text>
                    <Text style={[styles.headerText, { flex: 1, textAlign: 'right' }]}>Price</Text>
                  </View>
                  <FlatList<CartItem>
  data={items}
  keyExtractor={(item) => item.id}
  renderItem={renderItem}
  scrollEnabled={false}
/>

                  <View
                    style={{
                      borderBottomColor: '#aaa',
                      borderBottomWidth: 1,
                      borderStyle: 'dashed',
                      marginVertical: 2,
                    }}
                  />

                  <View style={styles.bottomRow}>
                    <Text style={styles.missedText}>Missed Something?</Text>
                    <TouchableOpacity style={styles.addButton}
                    onPress={() =>
                      router.push({
                        pathname: "/category",
                        params: { selectedItems: JSON.stringify(items) }, // send current cart items
                      })
                    }
                  >
                      <Text style={styles.addButtonText}>+ Add More Items</Text>
                    </TouchableOpacity>
                  </View>
                </View>

                {/* Pickup Section */}
                <Text style={styles.pickupTitle}>Pickup</Text>
                <View style={styles.pickupRow}>
                  <TouchableOpacity style={styles.pickupBtn} onPress={() => setShowDatePicker(true)}>
                    <Text style={styles.pickupBtnText}>{date ? date.toLocaleDateString() : 'Date'}</Text>
                    <Ionicons name="calendar" size={20} color="black" />
                  </TouchableOpacity>
                  <TouchableOpacity style={styles.pickupBtn} onPress={() => setShowTimePicker(true)}>
                    <Text style={styles.pickupBtnText}>{time ? time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Time'}</Text>
                    <Ionicons name="time" size={20} color="black" />
                  </TouchableOpacity>
                </View>

                {showDatePicker && (
                  <DateTimePicker
                    value={date || new Date()}
                    mode="date"
                    display="default"
                    onChange={(event, selectedDate) => {
                      setShowDatePicker(false);
                      if (selectedDate) setDate(selectedDate);
                    }}
                  />
                )}
                {showTimePicker && (
                  <DateTimePicker
                    value={time || new Date()}
                    mode="time"
                    display="default"
                    onChange={(event, selectedTime) => {
                      setShowTimePicker(false);
                      if (selectedTime) setTime(selectedTime);
                    }}
                  />
                )}

                {/* Bill Summary Section */}
                <View style={styles.billCard}>
                  <TouchableOpacity
                    style={styles.billHeader}
                    onPress={() => setShowBill(!showBill)}
                  >
                    <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                      <Ionicons name="receipt-outline" size={20} color="black" style={{ marginRight: 8 }} />
                      <Text style={styles.billTitle}>Bill Summary</Text>
                    </View>
                    <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                      <Text style={styles.billAmount}>₹{totalPay}</Text>
                      <Ionicons
                        name={showBill ? "chevron-up" : "chevron-down"}
                        size={18}
                        color="black"
                        style={{ marginLeft: 5 }}
                      />
                    </View>
                  </TouchableOpacity>

                  {showBill && (
                    <View style={styles.billDetails}>
                      <View style={styles.billRow}>
                        <Text style={styles.billText}>Item Total</Text>
                        <Text style={styles.billText}>₹{itemTotal}</Text>
                      </View>
                      <View style={styles.billRow}>
                        <Text style={styles.billText}>Handling Charge</Text>
                        <Text style={styles.billText}>₹{handlingCharge}</Text>
                      </View>
                      <View style={styles.billRow}>
                        <Text style={styles.billText}>Delivery Charge</Text>
                        <Text style={styles.billText}>₹{deliveryCharge}</Text>
                      </View>

                      <View style={styles.billDivider} />

                      <View style={styles.billRow}>
                        <Text style={styles.billTotalText}>To Pay</Text>
                        <Text style={styles.billTotalText}>₹{totalPay}</Text>
                      </View>
                    </View>
                  )}
                </View>
              </ScrollView>
            </View>

            {/* ✅ Sticky Bottom Bar */}
            <View style={styles.bottomBar}>
              <View style={styles.pickupRowBottom}>
                <Ionicons name="home" size={width * 0.06} color="#000" />
                <View style={styles.pickupTextContainer}>
                  <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                    <TouchableOpacity
                      style={{ flexDirection: 'row', alignItems: 'center' }}
                      onPress={() => setShowPickupOptions(true)}
                    >
                      <Text style={styles.pickupFrom}>Pickup from Home</Text>
                      <Ionicons
                        name="chevron-down"
                        size={width * 0.05}
                        color="#000"
                        style={{ marginLeft: width * 0.01 }}
                      />
                    </TouchableOpacity>
                  </View>
                  <Text style={styles.pickupAddress}>
  {locLoading ? 'Fetching current location...' : (pickupAddress || "No address set")}
</Text>

                </View>
              </View>

              <TouchableOpacity
  style={styles.payButton}
  onPress={() =>
    router.push({
      pathname: "/payments",
      params: {
        totalPay: totalPay.toString(),  // must be a string
        pickupAddress: pickupAddress,
      },
    })
  }
>
  <Text style={styles.payButtonText}>Click To Pay ₹{totalPay}</Text>
</TouchableOpacity>
            </View>

            {showPickupOptions && (
              <View style={styles.overlay}>
                <View style={styles.slidePanel}>
                  {/* Header */}
                  <View style={styles.slideHeader}>
                    <Text style={styles.slideTitle}>Select Address</Text>
                    <TouchableOpacity onPress={() => setShowPickupOptions(false)}>
                      <Ionicons name="close" size={26} color="#000" />
                    </TouchableOpacity>
                  </View>
           <TouchableOpacity
          style={[styles.addNewAddressBtn, styles.addNewAddressTop]}
          onPress={useMyCurrentLocation}
          disabled={locLoading}
>
         <FontAwesome name="map-marker" size={18} color="#34a853" style={{ marginRight: 8 }} />
         <Text style={styles.addNewAddressText}>Use my current Location</Text>
         {locLoading && (
         <ActivityIndicator style={{ marginLeft: 12 }} />
         )}
        </TouchableOpacity>

                  {/* Add New Address */}
                  <TouchableOpacity style={[styles.addNewAddressBtn, styles.addNewAddressCompactTop]} onPress={() => router.push('/SelectLocation')}>
                    <FontAwesome name="plus" size={18} color="#34a853" style={{ marginRight: 8 }} />
                    <Text style={styles.addNewAddressText}>Add New Address</Text>
                    <FontAwesome name="chevron-right" size={16} color="#000" style={{ marginLeft: 'auto' }} />
                  </TouchableOpacity>

                  {/* Saved Addresses */}
                  <Text style={styles.savedTitle}>Saved Addresses</Text>
{savedAddresses.length === 0 ? (
  <Text style={{ marginHorizontal: width * 0.04, color: '#777' }}>
    No saved addresses
  </Text>
) : (
  savedAddresses.map((addr, idx) => {
    const isSelected = (pickupAddress || "").trim() === addr.trim();
    return (
      <TouchableOpacity
        key={`saved-${idx}`}
        style={[styles.addressCard, { borderColor: isSelected ? '#2a9355' : '#ddd' }]}
        onPress={() => {
          setPickupAddress(addr);
          setShowPickupOptions(false); // close sheet on select
        }}
      >
        <Ionicons name="home" size={22} color="black" />
        <View style={{ flex: 1, marginLeft: 10 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center' }}>
            <Text style={styles.addressLabel}>Home</Text>

            {isSelected && (
              <View style={styles.selectedBadge}>
                <Text style={styles.selectedText}>Selected</Text>
              </View>
            )}
          </View>
          <Text style={styles.addressText}>{addr}</Text>
        </View>
      </TouchableOpacity>
    );
  })
)}
                </View>
              </View>
            )}
          </>
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  /* --- keep your styles unchanged --- */
  container: {
    flex: 1,
    backgroundColor: '#ffffff',
    padding: width * 0.05,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: height * 0.001,
    marginTop: height * 0.025,
  },
  headerTitle: {
    fontSize: width * 0.075,
    fontWeight: '400',
    color: '#113b68ff',
    fontFamily: 'LeagueSpartan-Bold',
  },
  /* rest of your styles unchanged ... */
  // (all other styles remain same as your provided code)
  card: {
    backgroundColor: '#f8f8f8',
    borderWidth: 1,
    marginTop:height*0.03,
    borderColor: '#e0e0e0',
    borderRadius: width * 0.025,
    overflow: 'hidden',
  },
  tableHeader: {
    flexDirection: 'row',
    paddingVertical: height * 0.012,
    paddingHorizontal: width * 0.04,
    borderBottomWidth: 1,
    borderColor: '#dddddd',
  },
  headerText: {
    flex: 1,
    fontWeight: '600',
    fontSize: width * 0.038,
    fontFamily: 'LeagueSpartan-Bold',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: height * 0.015,
    paddingHorizontal: width * 0.04,
    borderTopWidth: 1,
    borderColor: '#eaeaea',
  },
  itemName: {
    flex: 2,
    fontSize: width * 0.036,
    fontFamily: 'LeagueSpartan-Regular',
  },
  qtyContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  qtyButton: {
    paddingHorizontal: width * 0.02,
    paddingVertical: height * 0.004,
    marginHorizontal: width * 0.015,
    borderRadius: width * 0.01,
  },
  qtySymbol: {
    fontSize: width * 0.042,
    fontWeight: '600',
  },
  qtyText: {
    fontSize: width * 0.042,
    fontWeight: '600',
    fontFamily: 'LeagueSpartan-Regular',
  },
  itemPrice: {
    flex: 1,
    textAlign: 'right',
    fontSize: width * 0.036,
  },
  bottomRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: width * 0.04,
  },
  missedText: {
    color: '#000',
    fontSize: width * 0.036,
    fontFamily: 'LeagueSpartan-Regular',
  },
  addButton: {
    backgroundColor: '#CAFFE2',
    borderRadius: width * 0.015,
    paddingVertical: height * 0.008,
    paddingHorizontal: width * 0.025,
  },
  addButtonText: {
    color: '#000',
    fontWeight: '600',
    fontSize: width * 0.036,
    fontFamily: 'LeagueSpartan-Bold',
  },
  iconWrapper: {
    borderWidth: 2,
    borderColor: '#ccc6c6',
    borderRadius: 15,       
    padding: 4,
    width: width * 0.22,   
    height: height * 0.1, 
    justifyContent: 'center',
    alignItems: 'center',
  },
  cartIcon: {
    width: width * 0.2,
    height: height * 0.2,
    resizeMode: 'contain',
    opacity: 0.4,
  },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: width * 0.045,
    paddingTop: height * 0.05,
    paddingBottom: height * 0.015,
    backgroundColor: '#fff',
  },
  backBtn: {
    marginLeft: width * 0.03,
    marginRight: width * 0.03,
  },
  pickupTitle: {
    fontSize: width * 0.055,
    fontWeight: '500',
    marginTop: height * 0.04,
    marginLeft: width * 0.02,
    fontFamily: 'LeagueSpartan-Bold',
  },
  pickupRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    margin: width * 0.04,
    marginLeft: width * 0.02,
  },
  pickupBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: width * 0.03,
    paddingVertical: height * 0.012,
    paddingHorizontal: width * 0.04,
    flex: 1,
    marginHorizontal: width * 0.015,
    backgroundColor: '#fff',
  },
  pickupBtnText: {
    fontSize: width * 0.04,
    color: '#222',
    fontWeight: '600',
    fontFamily: 'LeagueSpartan-Regular',
  },
  billCard: {
    backgroundColor: '#f8f8f8',
    borderWidth: 1,
    borderColor: '#e0e0e0',
    borderRadius: width * 0.025,
    marginTop: height * 0.03,
    overflow: 'hidden',
  },
  billHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: width * 0.04,
  },
  billTitle: {
    fontSize: width * 0.04,
    fontWeight: '600',
    fontFamily: 'LeagueSpartan-Bold',
  },
  billAmount: {
    fontSize: width * 0.038,
    fontWeight: '600',
    fontFamily: 'LeagueSpartan-Bold',
  },
  billDetails: {
    paddingHorizontal: width * 0.04,
    paddingBottom: height * 0.015,
    fontFamily: 'LeagueSpartan-Regular',
  },
  billRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: height * 0.006,
  },
  billText: {
    fontSize: width * 0.036,
    color: '#333',
    fontFamily: 'LeagueSpartan-Regular',
  },
  billTotalText: {
    fontSize: width * 0.04,
    fontWeight: '700',
    fontFamily: 'LeagueSpartan-Bold',
  },
  billDivider: {
    borderBottomColor: '#ccc',
    borderBottomWidth: 1,
    borderStyle: 'dashed',
    marginVertical: height * 0.01,
  },
    bottomBar: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderColor: '#e0e0e0',
    padding: width * 0.04,
  },
  pickupRowBottom: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: height * 0.012,
  },
  pickupTextContainer: {
    marginLeft: width * 0.03,
    flex: 1,
    fontFamily: 'LeagueSpartan-Regular',
  },
  pickupFrom: {
    fontSize: width * 0.04,
    fontWeight: '600',
    color: '#000',
    fontFamily: 'LeagueSpartan-Bold',
  },
  pickupAddress: {
    fontSize: width * 0.032,
    color: '#666',
    marginTop: height * 0.004,
    fontFamily: 'LeagueSpartan-Regular',
  },
  payButton: {
    backgroundColor: '#CAFFE2',
    width: '90%',
    borderRadius: width * 0.03,
    borderWidth: 1,
    borderColor: '#9c9999ff',
    paddingVertical: height * 0.015,
    alignItems: 'center',
    marginLeft: width * 0.05,
  },
  payButtonText: {
    fontSize: width * 0.045,
    fontWeight: '600',
    color: '#000',
    fontFamily: 'LeagueSpartan-Regular',
  },
overlay: {
  position: 'absolute',
  bottom: 0,
  left: 0,
  right: 0,
  top: 0,
  backgroundColor: 'rgba(0,0,0,0.4)',
  justifyContent: 'flex-end',
},
slidePanel: {
  backgroundColor: '#f5f5f5',          // light grey background (panel)
  borderTopLeftRadius: width * 0.05,
  borderTopRightRadius: width * 0.05,
  height: height * 0.7,
  overflow: 'hidden',
},

slideHeader: {
  backgroundColor: '#fff',             // white header
  flexDirection: 'row',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: width * 0.04,
  borderBottomWidth: 1,
  borderColor: '#ddd',                 // thin divider
},

slideTitle: {
  fontSize: width * 0.045,
  fontWeight: '700',
  color: '#000',
  fontFamily: 'LeagueSpartan-Bold',
},

addNewAddressBtn: {
  flexDirection: 'row',
  alignItems: 'center',
  backgroundColor: '#fff',
  borderWidth: 1,
  borderColor: '#ddd',
  height: height * 0.07,
  borderRadius: width * 0.020,
  paddingVertical: height * 0.014, // reduced vertical padding
  paddingHorizontal: width * 0.04,
  marginHorizontal: width * 0.04, // keep horizontal margin
  marginVertical: height * 0.008, // reduced vertical margin to tighten gap
  shadowColor: '#000',
  shadowOffset: { width: 0, height: 2 },
  shadowOpacity: 0.08,
  shadowRadius: 4,
  elevation: 3, // for Android
  
},

addNewAddressTop: {
  marginTop: height * 0.04, // further increased top spacing for the first button
  marginBottom: height * 0.004, // tighten gap below the first button
},

addNewAddressCompactTop: {
  marginTop: height * 0.004, // reduce gap above the second button
},

addNewAddressText: {
  fontSize: width * 0.04,
  fontWeight: '500',
  marginLeft: 10,
  color: '#2a9355',
  fontFamily: 'LeagueSpartan-Regular',
},

savedTitle: {
  fontSize: width * 0.038,
  fontWeight: '500',
  marginLeft: width * 0.04,
  marginTop: height * 0.039,
  marginBottom: height * 0.01,
  color: '#000',
  fontFamily: 'LeagueSpartan-Bold',
},

addressCard: {
  flexDirection: 'row',
  alignItems: 'center',
  backgroundColor: '#fff',
  borderWidth: 1,
  borderColor: '#ddd',
  borderRadius: width * 0.025,
  padding: width * 0.035,
  marginHorizontal: width * 0.04,
  marginTop: height * 0.01,
  marginBottom: height * 0.010,
  shadowColor: '#000',
  shadowOffset: { width: 0, height: 2 },
  shadowOpacity: 0.08,
  shadowRadius: 4,
  elevation: 3, // for Android
},

addressLabel: {
  fontSize: width * 0.04,
  fontWeight: '600',
  color: '#000',
  marginRight: 8,
  fontFamily: 'LeagueSpartan-Bold',
},

selectedBadge: {
  backgroundColor: '#CAFFE2', 
  // light green background
  paddingHorizontal: 8,
  paddingVertical: 3,
  borderRadius: 9,             // pill shape
},

selectedText: {
  fontSize: width * 0.032,
  fontWeight: '600',
  color: '#2a9355',            // green text
  fontFamily: 'LeagueSpartan-Bold',
},

addressText: {
  fontSize: width * 0.032,
  color: '#555',
  marginTop: 2,
  fontFamily: 'LeagueSpartan-Regular',
},

  /* --- Empty state styles (added, without changing your original styles) --- */
  emptyContainer: {
    flex: 1,
    justifyContent: 'flex-start',
    alignItems: 'center',
    paddingHorizontal: width * 0.03,
    paddingTop: width * 0.07,
    backgroundColor: '#e7e3e3',
  },
  emptyCard: {
    backgroundColor: '#fff',
    width: '92%',
    borderRadius: width * 0.03,
    paddingVertical: height * 0.04,
    paddingHorizontal: width * 0.04,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 4,
  },
  emptyText: {
    marginTop: 9,
    fontSize: width * 0.042,
    fontWeight: '600',
    color: '#374151',
    fontFamily: 'LeagueSpartan-Regular',
  },
  addClothesButton: {
    marginTop: 16,
    backgroundColor: '#CAFFE2',
    paddingHorizontal: width * 0.06,
    width: width * 0.5,
    height: height * 0.035,
    alignItems: 'center',  
    justifyContent: 'center',
    borderRadius: width * 0.02,
  },
  addClothesText: {
    color: 'black',
    fontSize: width * 0.05,
    fontFamily: 'LeagueSpartan-Medium',
    textAlign: 'center',
    marginTop: -height * 0.005,
  },
});
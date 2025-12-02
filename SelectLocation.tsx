import { Ionicons } from '@expo/vector-icons';
import { useFonts } from 'expo-font';
import * as Location from 'expo-location';
import { useRouter } from 'expo-router';
import React, { useEffect, useState , useRef } from 'react';
import {
  Dimensions,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  Image,
  PixelRatio,
  Animated,
  Easing,
   TextInput,
  KeyboardAvoidingView,
  ScrollView,
  Modal,
  Platform 
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import MapView, { Marker, UrlTile, PROVIDER_GOOGLE, Region as RnRegion } from 'react-native-maps';

const { width, height } = Dimensions.get('window');

// 🔑 MapTiler API key (provided by you)
const MAPTILER_KEY = 'ER8AcLONjNZgjTKFnSW1';
// 🔑 Google Places API key (Web / Places key)
const GOOGLE_PLACES_API_KEY = 'AIzaSyDj4hV6pI21sKVuNr2xXHV5MZ3bKz7aohU';


function getMapTilerUrlTemplate() {
  const dpr = PixelRatio.get(); // 1, 1.5, 2, 3, ...
  // DPR >= 2 -> request higher-resolution tiles (no "256" segment)
  if (dpr >= 2) {
    return `https://api.maptiler.com/maps/streets-v4/{z}/{x}/{y}.png?key=${MAPTILER_KEY}`;
  }
  // DPR < 2 -> request explicit 256 tiles for compatibility
  return `https://api.maptiler.com/maps/streets-v4/256/{z}/{x}/{y}.png?key=${MAPTILER_KEY}`;
}

const LocationSelection: React.FC = () => {
  const [fontsLoaded] = useFonts({
    'LeagueSpartan-Regular': require('../assets/fonts/static/LeagueSpartan-Regular.ttf'),
    'LeagueSpartan-Bold': require('../assets/fonts/static/LeagueSpartan-Bold.ttf'),
    'LeagueSpartan-Medium': require('../assets/fonts/static/LeagueSpartan-Medium.ttf'),
  });

  const [useCustomMap, setUseCustomMap] = useState(true); // false = Google, true = MapTiler raster

  const [searchModalVisible, setSearchModalVisible] = useState(false);


  const [region, setRegion] = useState<RnRegion>({
    latitude: 17.385,
    longitude: 78.4867,
    latitudeDelta: 0.015,
    longitudeDelta: 0.015,
  });

  const [markerCoordinate, setMarkerCoordinate] = useState({
    latitude: 17.385,
    longitude: 78.4867,
  });

const [stateName, setStateName] = useState('');
const [district, setDistrict] = useState('');
const [pincode, setPincode] = useState('');


  const scaleAnim = useRef(new Animated.Value(1)).current;
  const rotateAnim = useRef(new Animated.Value(0)).current;

  const [address, setAddress] = useState('2nd Line');
  const [subAddress, setSubAddress] = useState('Sambassiva Peta, Sambassivarao Pet, GNT');
  const [locLoading, setLocLoading] = useState(false);

  type PlacePrediction = {
  place_id: string;
  description: string;
  structured_formatting?: {
    main_text: string;
    secondary_text?: string;
  };
};

const [searchQuery, setSearchQuery] = useState('');
const [predictions, setPredictions] = useState<PlacePrediction[]>([]);
const [isSearching, setIsSearching] = useState(false);


  const router = useRouter();

  useEffect(() => {
    getCurrentLocation();
  }, []);

  const fetchPlacePredictions = async (input: string) => {
  if (!input || input.length < 3) {
    setPredictions([]);
    return;
  }

  try {
    setIsSearching(true);

    const url =
      `https://maps.googleapis.com/maps/api/place/autocomplete/json` +
      `?input=${encodeURIComponent(input)}` +
      `&key=${GOOGLE_PLACES_API_KEY}` +
      `&components=country:in`; // limit to India, remove if not needed

    const res = await fetch(url);
    const json = await res.json();

    if (json.status === 'OK') {
      setPredictions(json.predictions || []);
    } else {
      console.log('Places autocomplete status:', json.status, json.error_message);
      setPredictions([]);
    }
  } catch (err) {
    console.error('Places autocomplete error:', err);
    setPredictions([]);
  } finally {
    setIsSearching(false);
  }
};
useEffect(() => {
  if (!searchQuery || searchQuery.length < 3) {
    setPredictions([]);
    return;
  }

  const timer = setTimeout(() => {
    fetchPlacePredictions(searchQuery);
  }, 400); // wait 400ms after typing stops

  return () => clearTimeout(timer);
}, [searchQuery]);
const handleSelectPrediction = async (prediction: PlacePrediction) => {
  try {
    const detailsUrl =
      `https://maps.googleapis.com/maps/api/place/details/json` +
      `?place_id=${prediction.place_id}` +
      `&key=${GOOGLE_PLACES_API_KEY}` +
      `&fields=geometry,formatted_address,address_components`;

    const res = await fetch(detailsUrl);
    const json = await res.json();

    if (json.status !== 'OK') {
      console.log('Place details error:', json.status, json.error_message);
      return;
    }

    const result = json.result;
    const { lat, lng } = result.geometry.location;

    // ---- extract state, district, pincode from Google components ----
let gState = '';
let gDistrict = '';
let gPincode = '';

(result.address_components || []).forEach((c: any) => {
  if (c.types.includes('administrative_area_level_1')) {
    gState = c.long_name;
  } else if (c.types.includes('administrative_area_level_2')) {
    gDistrict = c.long_name;
  } else if (c.types.includes('locality') && !gDistrict) {
    // fallback if district not present
    gDistrict = c.long_name;
  } else if (c.types.includes('postal_code')) {
    gPincode = c.long_name;
  }
});

setStateName(gState);
setDistrict(gDistrict);
setPincode(gPincode);


    // ⭐ SUPER FAST: Directly update region instead of using reverse geocode
    setRegion({
      latitude: lat,
      longitude: lng,
      latitudeDelta: 0.015,
      longitudeDelta: 0.015,
    });

    setMarkerCoordinate({ latitude: lat, longitude: lng });

    // ⭐ Instant bottom bar update (no waiting for reverse geocode)
    setAddress(result.formatted_address);

    const sub = result.address_components
      .map((c: any) => c.short_name)
      .join(', ');

    setSubAddress(sub);

    // close modal fast
    setSearchModalVisible(false);
    setSearchQuery('');
    setPredictions([]);

  } catch (err) {
    console.error('handleSelectPrediction error:', err);
  }
};


const handleSubmitSearch = async () => {
  if (searchQuery.trim().length === 0) return;

  // If predictions exist, select the first one
  if (predictions.length > 0) {
    handleSelectPrediction(predictions[0]);
    return;
  }

  // If no predictions yet, fetch first then select
  await fetchPlacePredictions(searchQuery);

  if (predictions.length > 0) {
    handleSelectPrediction(predictions[0]);
  }
};



  const handleToggleMapType = () => {
    // Button "pop" animation
    Animated.sequence([
      Animated.timing(scaleAnim, {
        toValue: 0.9,
        duration: 80,
        easing: Easing.out(Easing.quad),
        useNativeDriver: true,
      }),
      Animated.timing(scaleAnim, {
        toValue: 1,
        duration: 120,
        easing: Easing.out(Easing.quad),
        useNativeDriver: true,
      }),
    ]).start();

    // Rotate icon a bit each time
    Animated.timing(rotateAnim, {
      toValue: (useCustomMap ? 0 : 1),
      duration: 200,
      easing: Easing.out(Easing.quad),
      useNativeDriver: true,
    }).start();

    setUseCustomMap(prev => !prev);
  };

  const getCurrentLocation = async () => {
    setLocLoading(true);
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        console.log('Permission to access location was denied');
        setLocLoading(false);
        return;
      }

      await Location.enableNetworkProviderAsync().catch(() => {});

      const location = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.BestForNavigation,
      });

      const accuracy = location.coords.accuracy ?? Number.MAX_VALUE;

      if (accuracy > 100) {
        const betterLocation = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.Highest,
        }).catch(() => null);

        if (betterLocation?.coords.accuracy != null && betterLocation.coords.accuracy < accuracy) {
          const { latitude, longitude } = betterLocation.coords;
          updateLocationState(latitude, longitude);
          setLocLoading(false);
          return;
        }
      }

      const { latitude, longitude } = location.coords;
      updateLocationState(latitude, longitude);
    } catch (error) {
      console.error('Error getting location:', error);
      updateLocationState(17.385, 78.4867);
    } finally {
      setLocLoading(false);
    }
  };

  const updateLocationState = (latitude: number, longitude: number) => {
    const newRegion = {
      latitude,
      longitude,
      latitudeDelta: 0.015,
      longitudeDelta: 0.015,
    };
    setRegion(newRegion);
    setMarkerCoordinate({ latitude, longitude });
    reverseGeocode(latitude, longitude);
  };

  const reverseGeocode = async (latitude: number, longitude: number) => {
    try {
      const result = await Location.reverseGeocodeAsync({ latitude, longitude });
      if (result && result[0]) {
        const p = result[0];
        const street = p.name || p.street || '';
        const parts = [p.district, p.city, p.region].filter(Boolean);
        setAddress(street || (p.name ? p.name : 'Selected location'));
        setSubAddress(parts.join(', '));
        // fill state / district / pincode from Expo reverse geocode
setStateName(p.region || '');
setDistrict(p.subregion || p.city || p.district || '');
setPincode(p.postalCode || '');

      } else {
        setAddress('Selected location');
        setSubAddress('');
      }
    } catch (err) {
      console.error('reverseGeocode error', err);
      setAddress('Selected location');
      setSubAddress('');
    }
  };

  const onRegionChangeComplete = (newRegion: RnRegion) => {
    const lat = newRegion.latitude;
    const lng = newRegion.longitude;
    setMarkerCoordinate({ latitude: lat, longitude: lng });
    reverseGeocode(lat, lng);
    setRegion(newRegion);
  };

  const handleConfirmLocation = () => {
    router.push({
      pathname: '/add_address',
      params: {
        latitude: markerCoordinate.latitude.toString(),
        longitude: markerCoordinate.longitude.toString(),
        address,
        subAddress,
        state: stateName,
      district,
      pincode,
      },
    });
  };

  if (!fontsLoaded) {
    return (
      <SafeAreaView style={[styles.container, { justifyContent: 'center', alignItems: 'center' }]}>
        <Text>Loading...</Text>
      </SafeAreaView>
    );
  }

  const urlTemplate = getMapTilerUrlTemplate();

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#fff" />

      {/* Header */}
      <View style={styles.stickyHeader}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Ionicons name="arrow-back" size={width * 0.06} color="#000" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Select Your Location</Text>
        </View>

        <TouchableOpacity
  style={styles.searchContainer}
  activeOpacity={0.9}
  onPress={() => setSearchModalVisible(true)}
>
  <Ionicons name="search-outline" size={width * 0.05} color="#999" style={styles.searchIcon} />
  <Text style={styles.searchPlaceholder}>Search for your Location</Text>
</TouchableOpacity>


        {/* Toggle */}
      </View>

      {/* Map area */}
      <View style={styles.mapContainer}>
        <MapView
          provider={PROVIDER_GOOGLE}     // keep Google as base
          style={styles.map}
          initialRegion={region}
          region={region}
          onRegionChangeComplete={onRegionChangeComplete}
          showsUserLocation={true}
          showsMyLocationButton={true}
          mapType={useCustomMap ? 'none' : 'standard'}  // hide base when using custom
        >
          {useCustomMap && (
            <UrlTile
              urlTemplate={urlTemplate}
              maximumZ={18}
              flipY={false}
              zIndex={1}
              opacity={1}
            />
          )}

          <Marker coordinate={markerCoordinate} />
        </MapView>

        {/* Floating map-style switcher  */}
        <View style={styles.mapTypeSwitcher}>
          <Animated.View
            style={{
              transform: [
                { scale: scaleAnim },
              ],
            }}
          >
            <TouchableOpacity
              style={styles.mapTypeButton}
              onPress={handleToggleMapType}
              activeOpacity={0.8}
            >
              <Animated.View
                style={{
                  transform: [
                    {
                      rotate: rotateAnim.interpolate({
                        inputRange: [0, 1],
                        outputRange: ['0deg', '25deg'], // small tilt
                      }),
                    },
                  ],
                }}
              >
                <Ionicons name="layers-outline" size={width * 0.045} color="#000" />
              </Animated.View>
              <Text style={styles.mapTypeText}>
                {useCustomMap ? 'Google Map' : 'Custom Map'}
              </Text>
            </TouchableOpacity>
          </Animated.View>
        </View>
      </View>

{/* Search bottom sheet modal */}
<Modal
  visible={searchModalVisible}
  animationType="slide"
  transparent
  onRequestClose={() => setSearchModalVisible(false)}
>
  {/* semi–transparent background */}
  <TouchableOpacity
    style={styles.modalBackdrop}
    activeOpacity={1}
    onPress={() => setSearchModalVisible(false)}
  />

  <KeyboardAvoidingView
    behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    style={styles.modalContainer}
  >
    {/* Bottom sheet */}
    <View style={styles.modalSheet}>
      {/* White top part */}
      <View style={styles.modalTop}>
        <View style={styles.modalHeaderRow}>
          <Text style={styles.modalTitle}>Select Address</Text>

          <TouchableOpacity onPress={() => setSearchModalVisible(false)}>
            <Ionicons name="close" size={width * 0.05} color="#000" />
          </TouchableOpacity>
        </View>

        <View style={styles.modalSearchBox}>
          <Ionicons
            name="search-outline"
            size={width * 0.045}
            color="#999"
            style={styles.modalSearchIcon}
          />
        <TextInput
  placeholder="Search Address"
  placeholderTextColor="#999"
  style={styles.modalSearchInput}
  value={searchQuery}
  onChangeText={setSearchQuery}
  returnKeyType="search"
  onSubmitEditing={handleSubmitSearch}
/>

        </View>
      </View>

      {/* Grey body part */}
      <View style={styles.modalBody}>
        <ScrollView
  keyboardShouldPersistTaps="handled"
  contentContainerStyle={{ paddingTop: height * 0.015 }}
>

  {/* ------------------------------------------------ */}
  {/* SHOW PREDICTIONS ONLY WHEN USER IS TYPING        */}
  {/* ------------------------------------------------ */}
  {searchQuery.length > 0 && (
    <>
      {isSearching && (
        <Text style={styles.searchStatusText}>Searching…</Text>
      )}

      {predictions.map(pred => (
        <TouchableOpacity
          key={pred.place_id}
          style={styles.suggestionItem}
          onPress={() => handleSelectPrediction(pred)}
        >
          <Text style={styles.suggestionTitle}>
            {pred.structured_formatting?.main_text || pred.description}
          </Text>

          {pred.structured_formatting?.secondary_text ? (
            <Text style={styles.suggestionSubtitle} numberOfLines={1}>
              {pred.structured_formatting.secondary_text}
            </Text>
          ) : null}
        </TouchableOpacity>
      ))}
    </>
  )}

  {/* ------------------------------------------------ */}
  {/* SHOW "USE MY CURRENT LOCATION" WHEN NO TEXT     */}
  {/* ------------------------------------------------ */}
  {searchQuery.length === 0 && (
    <TouchableOpacity
      style={styles.useCurrentLocationBtn}
      onPress={() => {
        getCurrentLocation();
        setSearchModalVisible(false);   // close modal after selecting
      }}
    >
      <Ionicons
        name="locate-outline"
        size={width * 0.045}
        color="#21a45b"
        style={{ marginRight: width * 0.02 }}
      />
      <Text style={styles.useCurrentLocationText}>
        Use my current Location
      </Text>
    </TouchableOpacity>
  )}

</ScrollView>

      </View>
    </View>
  </KeyboardAvoidingView>
</Modal>


      {/* Sticky Bottom */}
      <SafeAreaView edges={['bottom']} style={styles.stickyBottom}>
        <View style={styles.locationCard}>
          <Text style={styles.locationTitle}>{address}</Text>
          <Text style={styles.locationSubtitle}>{subAddress}</Text>

          <TouchableOpacity
            style={[styles.confirmButton, locLoading ? { opacity: 0.6 } : null]}
            onPress={handleConfirmLocation}
            disabled={locLoading}
          >
            <Text style={styles.confirmButtonText}>{locLoading ? 'Fetching location...' : 'Confirm Location'}</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  stickyHeader: {
    backgroundColor: '#fff',
    paddingTop: 0,
    zIndex: 10,
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: width * 0.04,
    paddingVertical: height * 0.012,
  },
  backButton: { marginRight: width * 0.02 },
  headerTitle: {
    fontSize: width * 0.04,
    fontWeight: '400',
    color: '#000',
    marginLeft: width * 0.02,
    fontFamily: 'LeagueSpartan-Medium',
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#ada9a9ff',
    borderRadius: width * 0.03,
    height: height * 0.06,
    marginHorizontal: width * 0.04,
    marginTop: height * 0.02,
    marginBottom: height * 0.01,
    paddingHorizontal: width * 0.03,
    paddingVertical: height * 0.004,
    maxWidth: '100%',
  },
  searchIcon: { marginRight: width * 0.02 },
  searchPlaceholder: {
    flex: 1,
    fontSize: width * 0.035,
    color: '#999',
    fontFamily: 'LeagueSpartan-Regular',
  },

  toggleContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginVertical: 8,
    paddingHorizontal: width * 0.04,
  },
  toggleBtn: {
    paddingVertical: 8,
    paddingHorizontal: 15,
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 20,
    marginHorizontal: 5,
    backgroundColor: '#f3f3f3',
  },
  toggleActive: {
    backgroundColor: '#CAFFE2',
    borderColor: '#2a9355',
  },
  toggleText: {
    fontSize: 14,
    fontFamily: 'LeagueSpartan-Regular',
  },

  mapContainer: { flex: 1, backgroundColor: '#fff' },
  map: { width: '100%', height: '100%' },

  uploadPreview: {
    position: 'absolute',
    right: 12,
    top: 110,
    width: width * 0.22,
    height: height * 0.12,
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 6,
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 6,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.12,
  },
  uploadPreviewImage: { width: '100%', height: '70%' },

  stickyBottom: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: '#fff',
    paddingHorizontal: width * 0.04,
    paddingTop: height * 0.012,
    paddingBottom: height * 0.012,
    zIndex: 10,
    elevation: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.15,
    shadowRadius: 3,
  },
  locationCard: { backgroundColor: '#fff' },
  locationTitle: {
    fontSize: width * 0.04,
    color: '#000',
    fontWeight: '600',
    marginBottom: height * 0.005,
    marginLeft: width * 0.03,
    paddingTop: height * 0.005,
    fontFamily: 'LeagueSpartan-Semibold',
  },
  locationSubtitle: {
    fontSize: width * 0.032,
    color: '#666',
    marginBottom: height * 0.015,
    marginLeft: width * 0.03,
    marginTop: height * 0.002,
    fontFamily: 'LeagueSpartan-Regular',
  },
  confirmButton: {
    backgroundColor: '#CAFFE2',
    borderWidth: 1,
    borderColor: '#9c9999ff',
    paddingVertical: height * 0.015,
    borderRadius: width * 0.02,
    marginLeft: width * 0.073,
    marginTop: height * 0.0001,
    alignItems: 'center',
    width: width * 0.8,
    alignSelf: 'center',
  },
  confirmButtonText: {
    fontSize: width * 0.038,
    color: '#000',
    fontFamily: 'LeagueSpartan-Medium',
  },

  mapTypeSwitcher: {
    position: 'absolute',
    top: height * 0.12,         // adjust based on header height
    right: width * 0.04,
  },

  mapTypeButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#ffffff',
    paddingHorizontal: width * 0.03,
    paddingVertical: height * 0.008,
    borderRadius: 20,
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 3,
  },

  mapTypeText: {
    marginLeft: width * 0.015,
    fontSize: width * 0.032,
    color: '#000',
    fontFamily: 'LeagueSpartan-Regular',
  },
    modalBackdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.25)',
  },
  modalContainer: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  modalSheet: {
    borderTopLeftRadius: 18,
    borderTopRightRadius: 18,
    overflow: 'hidden',
    marginTop: 'auto',
  },
  // white section (title + search bar)
  modalTop: {
    backgroundColor: '#ffffff',
    paddingHorizontal: width * 0.05,
    paddingTop: height * 0.02,
    paddingBottom: height * 0.015,
  },
  modalHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: height * 0.015,
  },
  modalTitle: {
    fontSize: width * 0.06,
    color: '#000',
    fontFamily: 'LeagueSpartan-Medium',
  },
  modalSearchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#d3d3d3',
    paddingHorizontal: width * 0.03,
    height: height * 0.055,
  },
  modalSearchIcon: {
    marginRight: width * 0.02,
  },
  modalSearchInput: {
    flex: 1,
    fontSize: width * 0.035,
    fontFamily: 'LeagueSpartan-Regular',
    color: '#000',
  },
  // grey body
  modalBody: {
    backgroundColor: '#f4f4f4',
    paddingHorizontal: width * 0.05,
    paddingBottom: height * 0.02,
    minHeight: height * 0.4,
  },
  useCurrentLocationBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#acafadff',
    backgroundColor: '#ffffff',
    paddingVertical: height * 0.015,
    paddingHorizontal: width * 0.03,
    marginLeft: width * 0.01,
    marginRight: width * 0.01,
  },
  useCurrentLocationText: {
    fontSize: width * 0.035,
    color: '#21a45b',
    fontFamily: 'LeagueSpartan-Medium',
  },
    searchStatusText: {
    fontSize: width * 0.032,
    color: '#777',
    marginBottom: height * 0.008,
    fontFamily: 'LeagueSpartan-Regular',
  },
  suggestionItem: {
    paddingVertical: height * 0.012,
    borderBottomWidth: 1,
    borderBottomColor: '#e3e3e3',
  },
  suggestionTitle: {
    fontSize: width * 0.036,
    color: '#000',
    fontFamily: 'LeagueSpartan-Medium',
    marginBottom: 2,
  },
  suggestionSubtitle: {
    fontSize: width * 0.03,
    color: '#777',
    fontFamily: 'LeagueSpartan-Regular',
  },


});

export default LocationSelection;
